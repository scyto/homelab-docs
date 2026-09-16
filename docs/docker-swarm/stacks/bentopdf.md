---
title: "bentopdf swarm template"
---

# bentopdf swarm template

## Description
[bentopdf](https://github.com/alam00000/bentopdf) is a pdf toolkit: merge,
split, edit, sign, compress, convert, ocr. your files are processed in the
browser, the container only serves the page. by default the browser loads the
pdf engines from the jsdelivr cdn, so it needs internet access even though your
files don't leave it.

i use the `bentopdf-simple` image. it's the self-hosting build, the same tools
with the marketing pages taken out, not a cut down version.

!!! note

    use the upstream repo and images linked here. the docker hub image
    `bentopdf/bentopdf` is deprecated by the project and no longer updated, and
    some articles link to an old copy of the repo under another account.

## State Considerations for SWARM
none, there is nothing to keep so there are no volumes. upstream can hide tools
with a `config.json` mounted into the container at runtime, i don't use it

## Network Considerations
the container listens on 8080 (set `PORT` to change that), i publish it on 8091.
reach it on any swarm node IP or the keepalived IP, port 8091

## Placement Considerations
None, by default this template will result in a single replica

## Image Tag
upstream tags a release most months, so this is a plain version pin and renovate
opens a PR for each new one.

```yaml
services:
  bentopdf:
    image: ghcr.io/alam00000/bentopdf-simple:2.8.8
    ports:
      - 8091:8080
    deploy:
      mode: replicated
      replicas: 1
```
