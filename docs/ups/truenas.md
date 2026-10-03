---
title: "UPS on truenas1"
---

# ups on truenas1

truenas1 uses its built in UPS service, which is NUT, as the server for the
basement UPS. checked against TrueNAS 26.0.0-BETA.3 and NUT 2.8.1.

## the service

**System** > **Services** > **UPS**.

| field | value |
| --- | --- |
| Identifier | `ups-truenas` |
| UPS Mode | Master |
| Driver | the RMCARD205 entry, which uses `snmp-ups` |
| Port or Hostname | `192.168.1.72` |
| Monitor User | `upsmon` |
| Monitor Password | its own password |
| Remote Monitor | on |
| Shutdown Mode | UPS reaches low battery |
| Power Off UPS | off |
| Host Sync | `15` |

Auxiliary Parameters (ups.conf):

```text
snmp_version = v3
secLevel = authPriv
secName = nutups
authProtocol = SHA
privProtocol = AES
authPassword = <the auth key set on the card>
privPassword = <the privacy key set on the card>
ignorelb
override.battery.charge.low = 25
override.battery.runtime.low = 240
```

- the card only answers SNMPv3, so the login goes in the auxiliary parameters
- **Remote Monitor** makes `upsd` listen on the LAN, port 3493, so PeaNUT and
  Home Assistant can read it. NUT has no login for reads: anything on the LAN
  can read the UPS state. reads cannot change anything
- `ignorelb` makes the driver ignore the UPS's own low battery flag, which comes
  too late, and report low battery when the charge is under 25% or the runtime
  estimate is under 4 minutes. with **Shutdown Mode** on *UPS reaches low
  battery*, that is when truenas1 shuts down
- **Power Off UPS** is off, so the UPS stays on after truenas1 has shut down. it
  also feeds the basement network equipment. the cost: if mains returns before
  the battery is flat, truenas1 does not see power come back and stays off until
  someone starts it

## check it

from another machine:

```bash
printf 'LIST VAR ups-truenas\nLOGOUT\n' | nc -w 5 192.168.1.86 3493
```

`ups.status` should be `OL` (on mains), and `ups.load` and `battery.runtime`
should match the UPS's own display.

[gatus](../monitoring/gatus.md#checking-the-ups-cards-and-nut) connects to the
same port every minute as `nut truenas1`, asks the card's web server for `/`
as `ups card basement`, and asks prometheus for this server's `OL` flag as
`nut data truenas1`. the connect says `upsd` is up; the data check says it has
fresh data from the card; the card check is the one that catches a hung card,
see [what watches the cards](index.md#what-watches-the-cards).

## prometheus

the NUT exporter from the [prometheus-exporters sysext](../truenas/sysexts.md)
listens on `9199` and reads this host's NUT server by default. add the job to
`/mnt/fast/configs/prometheus/prometheus.yml`. prometheus reloads its config
on its own:

<!-- fragment: illustrative -->

```yaml title="/mnt/fast/configs/prometheus/prometheus.yml"
  - job_name: nut-truenas
    metrics_path: /ups_metrics
    scrape_interval: 60s
    params:
      ups: [ups-truenas]
    static_configs:
      - targets: ["192.168.1.86:9199"]
        labels:
          ups: ups-truenas
          node: truenas1
```

- `ups` is the NUT name, as **Identifier** above. the exporter answers `500`
  for a name the server doesn't list
- the exporter puts no label on a series saying which UPS or server it came
  from, so the job adds `ups` and `node`. gatus queries by them
- `60s`, the same as [unpoller](../monitoring/unpoller.md#prometheus). gatus
  asks once a minute, so a faster scrape buys nothing
- check the file before prometheus picks it up:

    ```bash
    sudo docker exec ix-prometheus-prometheus-1 promtool check config /config/prometheus.yml
    ```

the `nut-truenas` target is **UP** on prometheus's targets page, and this
returns one series with the value `1`:

```text
network_ups_tools_ups_status{ups="ups-truenas",flag="OL"}
```

a server the exporter can't read, because its driver has lost the card or
because it is down, fails the scrape with a `500`, so the target reads
**DOWN** and the query returns nothing. that is what the gatus check looks for.

## when it shuts down

on battery, at 25% charge or 4 minutes of runtime, whichever comes first.

truenas1 takes 72 seconds to shut down, measured, apps and pools included. 4
minutes is about three times that. the runtime is 14 to 15 minutes idle and 8
minutes during a model run, so in a model run the threshold is reached sooner.

`upsc ups-truenas@localhost` shows the thresholds as `battery.charge.low` and
`battery.runtime.low`, and `driver.flag.ignorelb: enabled`.
