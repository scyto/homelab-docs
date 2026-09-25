---
title: "omni-tools"
---

# omni-tools

[omni-tools](https://github.com/iib0011/omni-tools) is a web app full of small
tools: image, video and audio conversions, pdf tools, text and json formatting,
number and date calculators. the processing runs in your browser, and the
container only serves the page. it runs as one replica, anywhere on the swarm.
there is nothing to keep, so it has no volumes.

--8<-- "blocks/swarm/omni-tools/compose.yml.md"

## how it's reached

the container listens on 80, and i publish it on 8090. reach it on port 8090 of
any swarm node IP or the keepalived IP.

## latest, pinned by digest

upstream stopped tagging releases (`0.6.0` is from october 2025), but `latest`
is rebuilt from `main` on every merge. i pin `latest` by digest, so i get
current code and the compose still says which build is running. renovate opens
a PR when the digest changes.

to get the current digest, run:

```
docker buildx imagetools inspect iib0011/omni-tools:latest
```

## checking it

the page it serves should carry omni-tools' title:

```
curl -s http://192.168.1.45:8090/ | grep -o '<title>[^<]*</title>'
```

```text
<title>OmniTools</title>
```
