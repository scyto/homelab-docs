---
title: "UnPoller"
---

# unpoller

[UnPoller](https://unpoller.com) reads the UniFi controller and exports what it
finds for Prometheus: each device's uptime, port speeds and PoE draw, radio
channels, and which access point every client is on. it runs on truenas1.
checked against UnPoller 5.4.0, UniFi Network 10.6 and Prometheus 3.15.

i added it after a power test where working out which devices had restarted
meant reading each one's uptime by hand. the controller marks a device offline
minutes after the fact, and marks it offline when it only became unreachable.

--8<-- "blocks/truenas1/unpoller/compose.yml.md"

## before you deploy

1. on the controller, create a local admin called `unpoller` with view only
   access, used for nothing else
2. on truenas1, write its password to the file the stack binds:

    ```bash
    sudo mkdir -p /mnt/fast/configs/unpoller
    read -rs -p "UnPoller password: " P; echo
    printf '%s' "$P" | sudo tee /mnt/fast/configs/unpoller/unifi_pass > /dev/null
    unset P
    sudo chmod 600 /mnt/fast/configs/unpoller/unifi_pass
    ```

    - `read -rs` keeps the password off the screen and out of the shell history
    - `printf '%s'` writes no newline. check with `sudo wc -c`: the size is the
      length of the password
    - the container runs as root, so a root-only file is readable

3. record the same value in the [secret store](../secrets/add.md), as
   `unpoller_unifi_password`. the repo's checks fail a stack that binds a secret
   the store can't supply

## placement considerations

it runs on truenas1, not the swarm. Prometheus is there, and truenas1 is on a
different UPS from the proxmox cluster. on the swarm it would stop with the
cluster, which is when i most want its data.

## network considerations

it publishes `9130`. Prometheus on the same host is a catalog app on its own
docker network, so it scrapes `192.168.1.86:9130`, not the container by name.

## prometheus

add the job to `/mnt/fast/configs/prometheus/prometheus.yml`. Prometheus reloads
its config on its own:

<!-- fragment: illustrative -->

```yaml title="/mnt/fast/configs/prometheus/prometheus.yml"
  - job_name: unpoller
    scrape_interval: 60s
    static_configs:
      - targets: ["192.168.1.86:9130"]
```

- `60s` because UnPoller refreshes from the controller once a minute. it says so
  in its log at start
- check the file before Prometheus picks it up:

    ```bash
    sudo docker exec ix-prometheus-prometheus-1 promtool check config /config/prometheus.yml
    ```

it adds about 5,850 series for 23 devices and about 100 clients.

## check it works

- the container is `healthy`. the image carries its own healthcheck
- its log names the controller version and `Username: unpoller (has password: true)`
- the `unpoller` target is **UP** on Prometheus's targets page
- this returns one series per device:

    ```text
    unpoller_device_uptime_seconds
    ```

[gatus](gatus.md) checks it by asking Prometheus, not port `9130`:

```yaml title="swarm/gatus/config/40-truenas.yaml"
  - name: unpoller
    group: truenas
    url: "http://192.168.1.86:30104/api/v1/query?query=unpoller_device_uptime_seconds%20%3E%200"
    interval: 120s
    ui:
      resolve-successful-conditions: true
    conditions:
      - "[STATUS] == 200"
      - "[BODY].status == success"
      - "len([BODY].data.result) > 0"
```

that fails if UnPoller can't log in, if Prometheus stops scraping it, or if the
series go stale. a check on `9130` would pass with the login refused.

## queries i use

| question | query |
| --- | --- |
| which devices restarted in the last two hours | `unpoller_device_uptime_seconds < 7200` |
| clients on each access point | `sum by (name) (unpoller_device_stations)` |
| which access point a client is on | `unpoller_client_uptime_seconds`, by its `ap_name` label |
| a client that keeps roaming | `increase(unpoller_client_roam_count_total[1h])` |
| a port that lost its link | `unpoller_device_port_port_speed_bps == 0` |
| PoE draw per port | `unpoller_device_port_poe_watts` |
| an access point changing channel | `changes(unpoller_device_radio_channel[1h])` |

## what it does not collect

the controller's events: a device going offline, why a client was disconnected,
STP changes. UnPoller can send those to a log store, but the controller sends
them itself, by syslog, to [victorialogs](victorialogs.md), so `save_events`
and `save_alarms` are off here. per-application traffic and neighbouring
networks are off too.

a drop shorter than a minute shows as a client's uptime starting again, not as
a gap.
