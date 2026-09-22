---
title: "omni-tools swarm template"
---

# omni-tools swarm template

## Description
[omni-tools](https://github.com/iib0011/omni-tools) is a web app full of small
tools: image, video and audio conversions, pdf tools, text and json formatting,
number and date calculators. the processing runs in your browser, the container
just serves the page.

## State Considerations for SWARM
none, there is nothing to keep so there are no volumes

## Network Considerations
the container listens on 80, i publish it on 8090. reach it on any swarm node IP
or the keepalived IP, port 8090

## Placement Considerations
None, by default this template will result in a single replica

## Image Tag
upstream stopped tagging releases, `0.6.0` is from october 2025, but `latest` is
rebuilt from `main` on every merge. so i pin `latest` by digest: current code,
and the compose still says exactly which build is running. renovate opens a PR
when the digest changes.

to get the current digest:

```bash
docker buildx imagetools inspect iib0011/omni-tools:latest
```

```yaml
services:
  omni-tools:
    image: iib0011/omni-tools:latest@sha256:9a94e6ebc8dada2c7a5607b232214307e6f903a7747878602281ecdb79ced851
    ports:
      - 8090:80
    deploy:
      mode: replicated
      replicas: 1
```
