---
title: "cloudflare DDNS updater swarm template"
source_gist: https://gist.github.com/scyto/e7b022a02554e0e3bb2751b718eeda2d
---

# cloudflare DDNS updater swarm template

## Description
This template runs my cloudflare dynamic DNS updater.
It adjusts the default container cron job from 5 minutes to 1 minute because i have failover WAN ports.
The image is [archived upstream](https://github.com/oznu/docker-cloudflare-ddns). I still run it, pinned by digest.

## State Considerations for SWARM
none, this container is configured by env vars, except the API key, which is a swarm secret. An entrypoint wrapper reads it at startup, see [secrets](../secrets/index.md#option-3-an-entrypoint-wrapper).

## Network Considerations
none, this needs no special port mappings or other considerations

## Placement Considerations
None, by default this template will result in a single replica

--8<-- "blocks/swarm/cloudflare-ddns/compose.yml.md"
