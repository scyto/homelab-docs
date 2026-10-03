---
title: "UPS in the SMC closet"
---

# ups in the smc closet

the third UPS, added 2026-10-03. a CyberPower with an RMCARD205 at
`192.168.1.71`, in the basement SMC network closet. it feeds the closet's
network equipment, the distribution 10G PoE and 2.5GbE PoE switches and their
siblings, and syn02, and exists to take that load off the
[basement UPS](index.md) that truenas1 is on. checked against NUT 2.8.5 in the
container and the card's firmware 1.6.0.

nothing shuts down from it through NUT. the switches have no NUT, and syn02 has
its own UPS support, set by hand. NUT reads it so that [PeaNUT](peanut.md)
shows it, and PeaNUT only speaks to NUT servers.

## why a container

truenas1's own UPS service is NUT, but the TrueNAS UI configures one UPS,
[`ups-truenas`](truenas.md), and that one shuts the host down. so the third UPS
gets a second, independent `upsd` in a container on the same host, on port
`3494`. `3493` is the host's own.

--8<-- "blocks/truenas1/nut/compose.yml.md"

- the image is [instantlinux/nut-upsd](https://hub.docker.com/r/instantlinux/nut-upsd),
  alpine with the distribution's `nut` package, which has the `snmp-ups` driver
  and `upsc`. it is built to run `upsmon` as a monitor, which is not what this
  stack is for, so the compose file gives it a command of its own: write the
  NUT files, start the driver, run `upsd` in the foreground. no `upsd.users`,
  so nothing can log in; reads need no login
- the healthcheck is `upsc ups-smc@localhost ups.status`, which exits 1 when
  `upsd` is down, when the driver has gone, or when its data is stale, which
  is what a hung card looks like from here. docker on a standalone host does
  not act on unhealthy; it shows it
- if the card does not answer at start, the driver fails, the container exits
  and docker restarts it with its back-off until the card is back
- the second service is the same NUT exporter the
  [prometheus-exporters sysext](../truenas/sysexts.md) runs, started with
  `--nut.server=nut` so it reads this `upsd` over the stack's own network, and
  published on `9198`. the host's exporter on `9199` can't read it: its
  `serverport` parameter is ignored as of 3.3.0, so it only reaches servers on
  `3493`, and this one is on `3494`. the exporter keeps the image's own
  healthcheck, which says its HTTP side is up; a UPS the server doesn't list,
  or a driver that has lost the card, fails the scrape with a `500`

## before you deploy

1. the SNMPv3 user and keys are the same on all three cards, so the file is
   truenas1's own `ups.conf` with the name, the address and the description
   changed, and the low-battery lines dropped. on truenas1:

    ```bash
    sudo install -d -m 0750 -o root -g root /mnt/fast/configs/nut
    sudo sed -E -e 's/^\[ups-truenas\]/[ups-smc]/' -e '/^\s*desc\s*=/d' -e '/^\s*ignorelb/d' -e '/^\s*override\./d' -e 's/^(\s*port\s*=).*/\1 192.168.1.71/' -e 's/^\s+//' -e '/^\[/!s/^/\t/' -e 's/^(\tdriver\s*=.*)$/\1\n\tdesc = "SMC closet"/' /etc/nut/ups.conf | sudo tee /mnt/fast/configs/nut/ups.conf > /dev/null
    sudo chmod 0600 /mnt/fast/configs/nut/ups.conf
    sudo grep -c Password /mnt/fast/configs/nut/ups.conf
    ```

    - the last line prints `2`, one per key, without printing either
    - the result is this, with the keys filled in:

    <!-- fragment: illustrative -->

    ```text title="/mnt/fast/configs/nut/ups.conf"
    [ups-smc]
    driver = snmp-ups
    port = 192.168.1.71
    desc = "SMC closet"
    snmp_version = v3
    secLevel = authPriv
    secName = nutups
    authProtocol = SHA
    privProtocol = AES
    authPassword = <the auth key set on the card>
    privPassword = <the privacy key set on the card>
    ```

    - no `ignorelb` and no `override.*` lines: those move the low-battery
      threshold for a host that shuts down, and nothing shuts down from this
      UPS
    - root, mode `600`. the command in the stack runs as root and copies the
      file into place before dropping to `nut`
    - `create_host_path: false` on the bind, so a missing file fails the
      deploy instead of docker making a directory where the file should be

2. record the same text in the [secret store](../secrets/add.md) as
   `nut_smc_ups_conf_v1`, with step 6b in place of step 6. the whole file is
   the value: the keys are two of its lines and NUT reads them from nowhere
   else. answer **n** to *can rotate replace it on its own*: a new key has to
   be set on the three cards, in truenas1's UPS service and on the three
   proxmox nodes first. the repo's checks fail a stack that binds a secret
   the store can't supply

## peanut

the gear icon > **Manage Servers** > add:

| Name | Server Address | Port | Username | Password |
| --- | --- | --- | --- | --- |
| `ups-smc` | `192.168.1.86` | `3494` | empty | empty |

apply, then test, as on the [PeaNUT](peanut.md) page.

## check it

from another machine:

```bash
printf 'LIST VAR ups-smc\nLOGOUT\n' | nc -w 5 192.168.1.86 3494
```

`ups.status` should be `OL`, and `ups.load` and `battery.runtime` should match
the UPS's own display. on truenas1, `sudo docker ps` shows the `nut` container
`healthy`, and its log has `Connected to UPS [ups-smc]`. the exporter answers
with the same status as a series:

```bash
curl -s 'http://192.168.1.86:9198/ups_metrics?ups=ups-smc' | grep 'flag="OL"'
```

## prometheus

the stack's own exporter is the target, not the sysext's on `9199`. the job
is in `/mnt/fast/configs/prometheus/prometheus.yml` on truenas1, and
prometheus reloads its config on its own:

<!-- fragment: illustrative -->

```yaml title="/mnt/fast/configs/prometheus/prometheus.yml"
  - job_name: nut-smc
    metrics_path: /ups_metrics
    scrape_interval: 60s
    params:
      ups: [ups-smc]
    static_configs:
      - targets: ["192.168.1.86:9198"]
        labels:
          ups: ups-smc
          node: truenas1-nut
```

- `9198`, this stack's exporter. the sysext's exporter on `9199` would need
  `server` and a port, and it ignores the port, see above
- the exporter puts no label on a series saying which UPS or server it came
  from, so the job adds `ups` and `node`. `node` is `truenas1-nut`, not
  `truenas1`: that name is the host's own UPS service, on the
  [truenas1 page](truenas.md)
- `60s`, the same as the other NUT jobs. gatus asks once a minute
- check the file before prometheus picks it up:

    ```bash
    sudo docker exec ix-prometheus-prometheus-1 promtool check config /config/prometheus.yml
    ```

the `nut-smc` target is **UP** on prometheus's targets page, and this returns
one series with the value `1`:

```text
network_ups_tools_ups_status{ups="ups-smc",flag="OL"}
```

## what watches it

[gatus](../monitoring/gatus.md#checking-the-ups-cards-and-nut) gives it the
same three checks as the other UPSes, every minute: `ups card smc` asks the
card's web server for `/`, `nut ups-smc` connects to the stack's server on
`3494`, and `nut data ups-smc` asks prometheus for the `OL` flag the stack's
exporter last reported. the card check is the one that catches a hung card:

```yaml title="swarm/gatus/config/80-ups.yaml"
  - name: ups card smc
    group: ups
    url: "http://192.168.1.71/"
    client:
      ignore-redirect: true
    conditions:
      - "[CONNECTED] == true"
      - "[STATUS] < 400"
```

the other two are the same shape as every NUT server's: `nut ups-smc` is a
connect to `192.168.1.86:3494`, and `nut data ups-smc` asks prometheus for
`network_ups_tools_ups_status{ups="ups-smc",node="truenas1-nut",flag="OL"}`
over the last 150 seconds and wants `1`. see
[what watches the cards](index.md#what-watches-the-cards) for what each check
does and does not prove.

the card sends its log to [victorialogs](../monitoring/victorialogs.md#pointing-the-ups-cards-at-it)
like the other two, facility `local0`. its system name is `Small`, so it
arrives as hostname `Small` with `app_name` `UPS(192.168.1.71)`.
