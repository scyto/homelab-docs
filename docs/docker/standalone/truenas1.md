---
title: "truenas1"
---

# truenas1

the NAS, running TrueNAS on bare metal. the [truenas section](../../truenas/index.md) covers the box; this page is its docker side.

## the agent

a truenas custom app rather than a `docker run`, so truenas manages it with its other apps. see [truenas apps](../../truenas/apps.md).

## stacks from git

- [the arr stack](../../apps/arrstack.md)
- [frigate](../../apps/frigate.md)
- [dozzle agent](../../monitoring/dozzle.md) and [glances](../../monitoring/glances.md)

## run by truenas, not portainer

grafana, prometheus, ollama, open-webui, searxng and versitygw are truenas catalog apps, and a docker socket proxy is a custom app. they are managed in the truenas UI, not from git, see [truenas apps](../../truenas/apps.md).
