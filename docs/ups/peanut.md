---
title: "PeaNUT"
---

# peanut

[PeaNUT](https://github.com/Brandawg93/PeaNUT) is a small web dashboard for NUT.
it runs on truenas1 as the catalog app, and shows all three UPSes. checked against
PeaNUT 6.0.0.

## the app

**Apps** > **Discover Apps** > PeaNUT, with the defaults. the web UI is on port
`30224`.

## the servers

the gear icon > **Manage Servers**. one entry per NUT server:

| Name | Server Address | Port | Username | Password |
| --- | --- | --- | --- | --- |
| `ups-truenas` | `192.168.1.86` | `3493` | empty | empty |
| `ups-proxmox` | `192.168.1.81` | `3493` | empty | empty |
| `ups-smc` | `192.168.1.86` | `3494` | empty | empty |

- use the host's LAN address, even for the UPS on truenas1 itself. the app is a
  container on its own Docker network, so `127.0.0.1` is the container
- **apply before you test.** the test button only accepts a server that is
  already saved. testing a new address first fails with *Connection failed*, and
  the container log says `Connection to this server is not allowed`
- leave the username and password empty. they are only for sending commands to
  the UPS, and reading needs no login. `upsmon` is the account that decides when
  to shut down, so do not give it to a dashboard

the second entry is pve1, the proxmox node PeaNUT reads; pve2 and pve3 listen
on the LAN too, but only for prometheus. the third is the [`nut` container](smc.md) on truenas1, on its own port
beside the host's own NUT server, which is the first entry.

[gatus](../monitoring/gatus.md#checking-the-ups-cards-and-nut) connects to the
same servers every minute, as `nut truenas1`, `nut pve1` and `nut ups-smc`. if PeaNUT
shows a server as unreachable and gatus shows it green, the two disagree about
the port and that is worth a look; if both are red, the server is down. a
server that answers but shows stale data is red on its `nut data` check, with
its connect check still green, and the `ups card` checks say whether the card
itself still answers.
