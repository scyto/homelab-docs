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

## when it shuts down

on battery, at 25% charge or 4 minutes of runtime, whichever comes first.

truenas1 takes 72 seconds to shut down, measured, apps and pools included. 4
minutes is about three times that. the runtime is 14 to 15 minutes idle and 8
minutes during a model run, so in a model run the threshold is reached sooner.

`upsc ups-truenas@localhost` shows the thresholds as `battery.charge.low` and
`battery.runtime.low`, and `driver.flag.ignorelb: enabled`.
