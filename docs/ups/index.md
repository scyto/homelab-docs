---
title: "UPS"
---

# ups

two CyberPower UPSes, each with an RMCARD205 network card. NUT reads both, and
shuts down what each one feeds before the battery runs out. PeaNUT is the
dashboard.

| | basement | study |
| --- | --- | --- |
| NUT name | `ups-truenas` | `ups-proxmox` |
| model | CyberPower OR1500LCDRTXL2U, 1500 VA / 1125 W | CyberPower PR750LCD, 750 VA |
| card | RMCARD205, `192.168.1.72` | RMCARD205, `192.168.1.73`, firmware 1.6.0 |
| feeds | truenas1, the basement network equipment, an amplifier | pve1, pve2, pve3, the study rack switches |
| load | about 60%, of which truenas1 is about 28 points | 40 to 57% |
| runtime at that load | 14 to 15 minutes | 14 to 26 minutes |
| NUT server | truenas1's own UPS service | one on each proxmox node |
| shuts down | [truenas1](truenas.md) | [the proxmox cluster](proxmox.md) |

neither UPS has a USB cable to a host. NUT's `snmp-ups` driver reads the card
over the network, as an SNMPv3 user.

- [truenas1](truenas.md): the UPS service settings
- [proxmox](proxmox.md): NUT on the three nodes, and the scripts that take the
  cluster down together
- [PeaNUT](peanut.md): the dashboard

## how it fits together

- a host has to be able to find out that its own UPS is on battery without
  another host being up. so truenas1 runs its own NUT server, and every proxmox
  node runs its own driver, server and monitor against the study card. no node
  is a client of another
- the switch between a host and its UPS card has to stay up as long as the host
  does, so it is on the same UPS
- Home Assistant only reads. its NUT integration is a client. i do not run the
  NUT add-on, which is a server: Home Assistant is a VM on the cluster, so the
  thing announcing the power cut would be on the machines it was shutting down

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
