---
title: "UPS"
---

# ups

three CyberPower UPSes, each with an RMCARD205 network card. NUT reads all
three, and shuts down what the first two feed before the battery runs out. the
third feeds network equipment and is only read. PeaNUT is the dashboard.

| | basement | study | smc closet |
| --- | --- | --- | --- |
| NUT name | `ups-truenas` | `ups-proxmox` | `ups-smc` |
| model | CyberPower OR1500LCDRTXL2U, 1500 VA / 1125 W | CyberPower PR750LCD, 750 VA | CyberPower OR700LCDRM1U, 700 VA |
| card | RMCARD205, `192.168.1.72`, firmware 1.6.0 | RMCARD205, `192.168.1.73`, firmware 1.6.0 | RMCARD205, `192.168.1.71`, firmware 1.6.0 |
| feeds | truenas1, the basement network equipment, an amplifier | pve1, pve2, pve3, the study rack switches | the SMC closet's network equipment, the distribution 10G PoE and 2.5GbE PoE switches and their siblings, and syn02 |
| load | about 60%, of which truenas1 is about 28 points | 40 to 57% | about 27% |
| runtime at that load | 14 to 15 minutes | 14 to 26 minutes | about 29 minutes |
| NUT server | truenas1's own UPS service | one on each proxmox node | [the `nut` stack on truenas1](smc.md), port `3494` |
| shuts down | [truenas1](truenas.md) | [the proxmox cluster](proxmox.md) | nothing through NUT. syn02 watches it on its own |

no UPS has a USB cable to a host. NUT's `snmp-ups` driver reads the card
over the network, as an SNMPv3 user.

- [truenas1](truenas.md): the UPS service settings
- [proxmox](proxmox.md): NUT on the three nodes, and the scripts that take the
  cluster down together
- [smc closet](smc.md): the container that serves the third UPS, and why
- [PeaNUT](peanut.md): the dashboard

## how it fits together

- a host has to be able to find out that its own UPS is on battery without
  another host being up. so truenas1 runs its own NUT server, and every proxmox
  node runs its own driver, server and monitor against the study card. no node
  is a client of another
- the smc closet UPS shuts nothing down, so no host needs a server of its own
  for it. one `upsd` in a [container on truenas1](smc.md) serves it, for
  PeaNUT: truenas1's own UPS service configures one UPS, and that one is the
  basement's
- the switch between a host and its UPS card has to stay up as long as the host
  does, so it is on the same UPS
- Home Assistant only reads. its NUT integration is a client. i do not run the
  NUT add-on, which is a server: Home Assistant is a VM on the cluster, so the
  thing announcing the power cut would be on the machines it was shutting down

## what watches the cards

on 2026-10-03 at 11:15 the study card hung. its switch port stayed up, so the
network saw nothing wrong, and no check asked the card anything. twenty minutes
passed before anyone noticed. two things changed that day.

**gatus checks each card, the NUT servers, and whether each server's data is
fresh**, every minute, in
[its ups group](../monitoring/gatus.md#checking-the-ups-cards-and-nut):

| check | what it proves |
| --- | --- |
| `ups card basement`, `ups card study`, `ups card smc` | the card's web server answers `/` itself. a hung card answers nothing |
| `nut truenas1`, `nut pve1`, `nut ups-smc` | the NUT server accepts a connection, on `3493`, or `3494` for the [smc closet](smc.md) stack |
| `nut data truenas1`, `nut data pve1`, `nut data pve2`, `nut data pve3`, `nut data ups-smc` | prometheus holds that server's `OL` flag at `1`, read from it by the NUT exporter within the last minute |

- the server check says the server is up, not that its data is fresh. `upsd`
  keeps answering when its driver has lost the card, and reports `DATA-STALE`
  over the NUT protocol, which gatus can't speak
- the data check is what catches stale data. the NUT exporter on truenas1
  reads each server over the NUT protocol every time prometheus scrapes it,
  and a server with nothing fresh fails the scrape, so prometheus has nothing
  for it and the check goes red. on battery the flag is `0` and the check goes
  red too, which is the alert. the tooltip tells the two apart: `0` is a power
  cut, `(INVALID)` is nothing to read
- every proxmox node gets a data check because each node shuts itself down
  from its own driver, so one node's driver can be stale while another's is
  fine

**each card sends its log to [victorialogs](../monitoring/victorialogs.md)**,
so the card's own events, link, reboot, power, are on record, and the next hang
is read from what the card said last instead of inferred from silence. on each
card, **Log** > **Syslog**:

1. facility code **Local 0**
2. **Add Server**: `192.168.1.86`, port `514`, UDP
3. **Send test**. the store should show `This is test message from <the
   card's address>`

what arrives:

- the card sends its own system name as the syslog hostname, so the basement
  card is `Bottom`, the study card is `Shelf` and the smc closet card is
  `Small`, with `app_name` `UPS(192.168.1.72)`, `UPS(192.168.1.73)` and
  `UPS(192.168.1.71)`
- nothing else on the lan uses `local0`, so `facility_keyword:local0` is the
  cards and nothing else:

    ```bash
    curl -s -u logs 'http://192.168.1.86:9428/select/logsql/query?query=facility_keyword:local0&limit=20'
    ```

## the UPS switches itself off, and that is what brings everything back

when a host shuts down for a power cut, the last thing NUT does is tell the UPS
to turn its output off and come back when mains returns. the UPS waits 180
seconds (`ups.delay.shutdown`), then turns off.

when mains returns the UPS turns its output on, the hosts see power arrive, and
they boot. the BIOS on each host is set to power on when power returns. without
the UPS turning off, the hosts would shut down, the UPS would stay on, and they
would wait for someone to press a button.

for this to work the SNMP user on the card has to be allowed to control the UPS,
not only read it.

## the model's power cap

truenas1's GPU is [capped at 350 W](../truenas/hardware-and-base-install.md), set
again at every boot. uncapped, a model run took the basement UPS from 61% to
106% and truenas1 lost power a few minutes later. capped, the same run holds at
86 to 87% with 8 minutes of runtime.

## numbers worth keeping

measured on 2026-10-01.

| | |
| --- | --- |
| basement UPS with truenas1 off | 33%, about 375 W |
| truenas1 idle | about 310 W |
| a capped model run | adds about 300 W |
| a full shutdown of the proxmox cluster | 2 minutes 42 seconds |
| slowest guest to stop | Home Assistant, 62 seconds |
| battery used in 5 minutes on the study UPS, at about 48% load | 7 points |
