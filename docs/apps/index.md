---
title: "Apps"
---

# apps

these pages cover what runs on the platform, and why each app is set up the way
it is. each page shows its stack's files from git, and the text repeats a
fragment only where something is unusual enough to need one.

- every app is a stack in git, at `stacks/<env>/<stack>/compose.yml`. portainer
  deploys it to the swarm or to a
  [standalone host](../docker/standalone/index.md), see
  [stacks in git](../docker/gitops-with-portainer.md)
- the [conventions](../docker/conventions.md) are named binds, digests,
  `deploy.labels`, the time zone and secrets as files. not every stack meets all
  of them: several images have a tag and no digest, frigate and the arr stack
  use plain binds, and oauth2-proxy's cookie secret is an environment variable
- the [swarm](../docker/index.md#swarm-deployed-stacks) page and each standalone
  host's page list what runs where

| group | apps |
| --- | --- |
| dns and network | [adguard](adguard.md), [cloudflare ddns](cloudflare-ddns.md), [nginx proxy manager](nginx-proxy-manager.md), [oauth2-proxy](oauth2-proxy.md) |
| certificates | acme.sh for the [ASRock Rack BMC](acme-asrock-bmc.md) and [Synology DSM](acme-synology.md) |
| media and home | [the arr stack](arrstack.md), [frigate](frigate.md), [infinitude](infinitude.md), [mosquitto](mosquitto-mqtt.md) |
| web and tools | [wordpress](wordpress.md), [omni-tools](omni-tools.md), [bentopdf](bentopdf.md) |
| swarm plumbing | [auto-label nodes](auto-label-nodes.md) |

the monitoring stacks are in [monitoring](../monitoring/index.md).
