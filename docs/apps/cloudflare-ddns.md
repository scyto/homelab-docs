---
title: "cloudflare DDNS updater swarm template"
source_gist: https://gist.github.com/scyto/e7b022a02554e0e3bb2751b718eeda2d
---

# cloudflare DDNS updater swarm template

## Description
This template runs my cloudflare dynamic DNS updater.
It adjust the default container cron job from 5 minutes to 1 minute because i have failover WAN ports.

Update as of 2026.09.24: this is how i first set it up. what i run now is [at the end](#what-i-run-now).

## State Considerations for SWARM
none, this container can be cofigured entirely by env vars so i use those

## Network Considerations
none, this need no special port mappings or other considerations
consider using an secret to store the API

## Placement Considerations
None, by default this template will result in a single replica

```
version: '3'
services:
  cloudflare-ddns:
    image: oznu/cloudflare-ddns:latest
    restart: always
    environment:
      - API_KEY=<redacted>
      - ZONE=mydomain.com
 #     - SUBDOMAIN=subdomain
      - PROXIED=false
      - CRON=*/1 * * * *
```

## what i run now

- the image is [archived upstream](https://github.com/oznu/docker-cloudflare-ddns). i still run it, pinned by digest
- the api key is a swarm secret. an entrypoint wrapper reads it at startup, see [secrets](../secrets/index.md#option-3-an-entrypoint-wrapper)

--8<-- "blocks/swarm/cloudflare-ddns/compose.yml.md"
