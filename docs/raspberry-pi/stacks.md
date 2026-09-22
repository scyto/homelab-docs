---
title: "Docker & Stacks"
---

# docker and stacks

the pi is a [standalone docker host](../docker/standalone/index.md): its own environment in portainer, its stacks deployed from git like the swarm's.

## docker

Docker CE from Docker's own apt repository, the same setup
[get.docker.com](../docker/swarm/install-docker.md) creates:

```
/etc/apt/keyrings/docker.asc
/etc/apt/sources.list.d/docker.list:
  deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable
```

no `/etc/docker/daemon.json`, and `containerd`'s config is the package default
(`disabled_plugins = ["cri"]`). nothing tuned.

## portainer agent

started by hand once, not from git, because it is what lets portainer deploy
everything else here:

```
docker run -d -p 9001:9001 --name portainer_agent --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  -v /:/host \
  portainer/agent:lts
```

keep it on the same version as the portainer server.

## radios

the USB radios are passed to containers by their `/dev/serial/by-id/` names, so
they land on the right device whatever order they enumerate in.

| radio | by-id name starts | used by |
| --- | --- | --- |
| Zooz 800 Z-Wave stick | `usb-Zooz_800_Z-Wave_Stick_` | zwave-js-ui |
| Nabu Casa SkyConnect | `usb-Nabu_Casa_SkyConnect_v1.0_` | ser2net |
| Sonoff Zigbee 3.0 USB Dongle Plus | `usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_` | zigbee2mqtt, not deployed yet |

## containers

each stack polls its own `deploy/pi-zwave01/<stack>` branch, see [stacks in git](../docker/gitops-with-portainer.md).

### zwave-js-ui

the Z-Wave network, driving the Zooz 800 stick. Home Assistant's Z-Wave JS integration connects to it.

| | |
| --- | --- |
| network | its own bridge |
| ports | `80` to the UI on 8091, `3000` for the Z-Wave JS websocket Home Assistant uses |
| data | `/docker-data/zwavejs2mqtt/store`: settings, network keys, node cache |

- renovate never bumps it on its own. it has to stay compatible with Home Assistant's integration, and an upgrade migrates the node database one way, so i approve each one when i can watch Home Assistant afterwards
- the store directory keeps its old `zwavejs2mqtt` name. renaming it means changing the stack too

### ser2net

shares the SkyConnect over the network on TCP port `8000`, so Home Assistant's OpenThread Border Router add-on can use the radio from its VM. the config and why each line is there are on [thread radio](thread-radio.md).

| | |
| --- | --- |
| network | host |
| ports | `8000` |
| data | `/docker-data/ser2net/data/ser2net.yaml` |

its healthcheck looks for an established connection on port `8000`, so healthy means a client is attached. unhealthy usually means the add-on is down, but ser2net failing to start, read its config or open the radio looks the same. check the connection first, then its logs.

### dozzle agent

serves this host's container logs to the [dozzle](../monitoring/dozzle.md) hub on the swarm, on port `7007`. the certificate pair it authenticates with is in `/docker-data/dozzle`.

### glances

host metrics for the [dashboard](../monitoring/glances.md), on port `61208`. host networking so it sees the pi's real interfaces, and an empty directory from the root filesystem mounted read-only, so it reports the pi's own disk.

## /docker-data

every stack's state lives under one directory, so one directory is what gets
[backed up](../backups/pi-host-backup.md):

| path | holds |
| --- | --- |
| `/docker-data/zwavejs2mqtt/store` | the Z-Wave network: settings, keys, node cache, logs |
| `/docker-data/ser2net/data` | `ser2net.yaml` |
| `/docker-data/dozzle` | the dozzle agent's certificate pair |
| `/docker-data/zigbee2mqtt/data` | zigbee2mqtt config and database |
