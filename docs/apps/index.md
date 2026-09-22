---
title: "Apps"
---

# apps

what runs on the platform, and why each app is set up the way it is. these pages describe the architecture and point at the config; they only show fragments where something is unusual enough to need one.

- every app is a stack in git, `stacks/<env>/<stack>/compose.yml`, deployed by portainer to the swarm or to a [standalone host](../docker/standalone/index.md), see [stacks in git](../docker/gitops-with-portainer.md)
- every stack follows the same [conventions](../docker/conventions.md): named binds, digests, `deploy.labels`, the time zone, secrets as files
- what runs where is listed on the [swarm](../docker/index.md#swarm-deployed-stacks) and each standalone host's page

| group | apps |
| --- | --- |
| dns and network | [adguard](adguard.md), [cloudflare ddns](cloudflare-ddns.md), [nginx proxy manager](nginx-proxy-manager.md), [oauth2-proxy](oauth2-proxy.md) |
| certificates | acme.sh for the [ASRock Rack BMC](acme-asrock-bmc.md) and [Synology DSM](acme-synology.md) |
| media and home | [the arr stack](arrstack.md), [frigate](frigate.md), [infinitude](infinitude.md), [mosquitto](mosquitto-mqtt.md) |
| web and tools | [wordpress](wordpress.md), [omni-tools](omni-tools.md), [bentopdf](bentopdf.md) |
| swarm plumbing | [auto-label nodes](auto-label-nodes.md) |

the monitoring stacks are in [monitoring](../monitoring/index.md).
