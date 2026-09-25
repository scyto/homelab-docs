---
title: "Homepage"
---

# homepage dashboard

[homepage](https://gethomepage.dev/) runs on the swarm on port `3000`. it's one page with three tabs: apps, infrastructure and plumbing.

--8<-- "blocks/swarm/homepage/compose.yml.md"

## before you deploy

1. create both folders on the cephfs mount, owned by uid 1000, which homepage and config-sync run as:

    ```
    sudo mkdir -p /mnt/docker-cephFS/homepage_config/secrets /mnt/docker-cephFS/homepage_git_v2
    sudo chown -R 1000:1000 /mnt/docker-cephFS/homepage_config /mnt/docker-cephFS/homepage_git_v2
    ```

    - a missing folder fails the task, because each volume binds its folder by path

2. put each widget key in its own file in `homepage_config/secrets/`, readable by uid 1000. there's one file for each `HOMEPAGE_FILE_*` path under `/app/config/secrets/`

    - a missing key file leaves that tile's widget showing an api error

3. create the docker secret `unifi_apikey`. homepage shares `gitsync_ssh_key_v1` and the `discovery` overlay with gatus, so create those as in [gatus's steps](gatus.md#before-you-deploy) if gatus is not deployed yet

## where the tiles come from

- labels on the stacks make the tiles for anything with a web UI. homepage reads them from two docker endpoints: `dockerproxy`, the swarm's read-only socket proxy on an overlay network, and a second read-only socket proxy on truenas1 at 192.168.1.86:2375.

    --8<-- "blocks/swarm/homepage/config/docker.yaml.md"

- on the swarm the labels go under `deploy.labels`. homepage reads the swarm's service specs, and container labels aren't in them, so a tile labelled the usual way never appears
- `services.yaml` holds everything else: the portainer environments, truenas, unifi, proxmox and its nodes, glances on each host, and the plumbing tab

--8<-- "blocks/swarm/homepage/config/services.yaml.md"

--8<-- "blocks/swarm/homepage/config/widgets.yaml.md"

## config in git

homepage has no setting for where its config lives, so it can't read a git checkout the way [gatus](gatus.md) does. a git-sync sidecar in the same stack polls `deploy/swarm/homepage` and runs a small script after each sync that copies `config/*.yaml` and `custom.css` into homepage's config volume. homepage notices and reloads.

- the script reconciles: a file removed from git disappears from the volume too
- it refuses to run against an empty checkout, so a bad ref can't wipe the dashboard
- it writes each file to a temporary name and renames it, so homepage never reads half a file
- it never touches the key files, which live in the same volume

--8<-- "blocks/swarm/homepage/sync-config.sh.md"

the sidecar is the one on [config from git](../docker/config-from-git.md), with two additions. `GITSYNC_EXECHOOK_COMMAND` runs `sync-config.sh`, mounted from a swarm config, after each sync. the sidecar also mounts homepage's `config` volume, which the script writes to.

--8<-- "blocks/swarm/homepage/sparse-checkout.md"

--8<-- "blocks/swarm/homepage/ssh_config.md"

--8<-- "blocks/swarm/homepage/known_hosts.md"

## tabs and layout

--8<-- "blocks/swarm/homepage/config/settings.yaml.md"

```yaml title="config/settings.yaml"
layout:
  Arr:
    tab: Apps
    style: column
  Infrastructure:
    tab: Infrastructure
    style: row
    columns: 4
```

- every group names its tab. a group without one shows on every tab, and so does a group discovered from a label but missing from `layout`
- apps groups are columns, side by side. infrastructure and plumbing groups are rows of four, glances rows of three
- `maxGroupColumns: 6` lets up to six groups sit side by side on a wide screen. homepage's page stops growing at 1792px, and six columns in that width would only mean narrower ones, so `custom.css` lifts that cap to 2560px on wider screens

## widgets and their keys

labels are readable by anything that can read the service, so no key or password goes in one. the label names a placeholder, and homepage fills it from a file:

```yaml title="arrstack/compose.yml"
    labels:
      - homepage.widget.type=qbittorrent
      - homepage.widget.url=http://192.168.1.86:8080
      - homepage.widget.username=admin
      - homepage.widget.password={{HOMEPAGE_FILE_QBITTORRENT_PASSWORD}}
```

```yaml title="compose.yml"
    environment:
      - HOMEPAGE_FILE_QBITTORRENT_PASSWORD=/app/config/secrets/qbittorrent_password
```

the file can also be a docker secret: `HOMEPAGE_FILE_UNIFI_KEY=/run/secrets/unifi_apikey`. the other keys are read-only where the app allows it: a proxmox auditor token, a read-only truenas api key. the portainer key belongs to a helpdesk-role user and has read access.

- check the upstream's lockout rules before testing a password. qbittorrent bans an address for an hour after five failed logins, and homepage's address is its node's
- the adguards are macvlan containers, which a container on the same host can't reach. a shim on every swarm node covers their two IPv4 addresses only, so the adguard widgets use those addresses and work wherever homepage runs. the shim is in [troubleshooting](../docker/troubleshooting.md#a-container-cant-reach-a-macvlan-container-on-the-same-host)
- to test a widget, ask homepage's own proxy from inside its container. use the widget's endpoint name, not the upstream's api path:

    ```
    wget -q -O - 'http://127.0.0.1:3000/api/services/proxy?group=Downloads&service=qBittorrent&endpoint=torrents'
    ```

## plumbing tiles show gatus

the plumbing tab holds things with no web UI. each tile shows its [gatus](gatus.md) check through a `customapi` widget, and none has a container status badge:

```yaml title="config/services.yaml"
    - Mosquitto:
        icon: mosquitto.png
        description: MQTT broker, 1883
        widget:
          type: customapi
          url: http://192.168.1.45:8085/api/v1/endpoints/plumbing_mosquitto/statuses?page=1&pageSize=1
          refreshInterval: 60000
          mappings:
            - field: results.0.success
              label: Gatus
              format: text
              remap:
                - value: true
                  to: UP
                - value: false
                  to: DOWN
                - any: true
                  to: "?"
            - field: results.0.duration
              label: Response
              format: float
              scale: "1/1000000"
              suffix: ms
```

- there are no badges because homepage can only take one from docker, kubernetes, proxmox, a ping or its own http check, not from gatus. and a mix of `running 1/1`, `running` and `healthy` side by side said different things

## glances tiles open glances

homepage only links a tile's icon and name, and the glances widget covers the rest of the tile. `custom.css` stretches the name's link over the whole tile on tiles with `id: glances-<host>`:

--8<-- "blocks/swarm/homepage/config/custom.css.md"

## the stale page after a restart

homepage serves a prebuilt page, and after a restart that page has the image's placeholder settings: no tabs, no layout. a browser only asks homepage to rebuild it when the config has changed since it last looked, so after a restart it can keep showing the placeholder. to rebuild it, run this from inside the container, then reload the page:

```
wget -q -O - http://127.0.0.1:3000/api/revalidate
```

## checking it

the page homepage serves should carry all three tabs:

```
curl -s http://192.168.1.45:3000/ | grep -o '"tab":"[^"]*"' | sort -u
```

```text
"tab":"Apps"
"tab":"Infrastructure"
"tab":"Plumbing"
```

no output means it is serving the placeholder page. to fix it, see [the stale page after a restart](#the-stale-page-after-a-restart).
