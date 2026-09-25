---
title: "syn02"
---

# syn02

a synology NAS running docker through Synology's Container Manager package. docker's data is under `/volume1/@docker`, not `/var/lib/docker`.

## the agent

a `docker run` like the pi's, see [add a host](add-a-host.md). on DSM the volumes mount is `/volume1/@docker/volumes:/var/lib/docker/volumes`.

## stacks from git

- watch-your-lan - flags new devices on the lan. host networking, watching `ovs_eth0`, the UI on port `8840`, data in `/volume1/docker/wyl/data`
- [dozzle agent](../../monitoring/dozzle.md) - its certificate pair is in `/volume1/docker/dozzle`
- [glances](../../monitoring/glances.md)

## DSM differences

- DSM has no `/etc/os-release`, so glances would report the container's OS. its stack binds DSM's `/etc/VERSION` read-only and builds an `os-release` from it at start
- `ovs_eth0` is the LAN interface, not `eth0`: DSM puts the port on an Open vSwitch bridge
- stack data lives under `/volume1/docker/<stack>`, the share DSM creates for it
