---
title: "watchtower swarm template"
source_gist: https://gist.github.com/scyto/38d05c98b18ce7ea57002583f1ebc449
---

!!! warning "Deprecated: I no longer run this"

    Watchtower only updates standalone containers, not swarm services, so on a
    swarm it was only ever managing part of my estate. It also had no notion of
    which updates I actually wanted, so anything on a rolling tag moved whenever
    upstream moved.

    Replaced by [Renovate](../image-updates-renovate.md), which proposes updates
    as pull requests against the compose files in git instead of changing what is
    running. That gives me a diff, a changelog link, and the option to say no.
    The compose is now the source of truth, so an updater that edits running
    containers behind git's back is working against the setup rather than with
    it.

    Kept for reference. Nothing here is wrong, it just is not what I do now.

# watchtower swarm template

## Description
This template runs watchtower.  This is new for me so still seeing if i like it!
(fingers cross this works, yes need to setuyp smtp email at some point, lol)

## State Considerations for SWARM
none, this container can be cofigured entirely by env vars so i use those

## Network Considerations
none, no published port is needed

## Placement Considerations
None, by default this template will result in a single replica. 


```
version: "3"

services:
  watchtower:
   image: containrrr/watchtower 
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock
   environment:
     WATCHTOWER_SCHEDULE: 0 0 4 * * *
     TZ: America/Los_Angeles
     WATCHTOWER_CLEANUP: "true"
     WATCHTOWER_DEBUG: "true"
```
