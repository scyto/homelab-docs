---
title: "Standalone Hosts"
---

# standalone docker hosts

three hosts run plain docker, not swarm. each runs a portainer agent and is its own environment in portainer. their stacks deploy from git the same way as the swarm's, with one directory and one `deploy/<host>/<stack>` branch per stack, see [stacks in git](../gitops-with-portainer.md).

| host | what it is |
| --- | --- |
| [truenas1](truenas1.md) | the NAS. the arr stack and frigate run here to sit next to its storage and accelerators |
| [syn02](syn02.md) | a synology NAS |
| [pi-zwave01](pi-zwave01.md) | a raspberry pi 4 with the usb radios plugged into it |

[adding a host](add-a-host.md) is an agent and an environment in portainer.

## how they differ from the swarm

- compose keys the swarm ignores work here: `container_name`, `restart`, `devices`, `network_mode: host`
- labels go under `labels`, not `deploy.labels`. there is no service spec to hang them on
- healthchecks are fine. on a standalone host docker only reports an unhealthy container, where swarm would kill the task and reschedule it
- bind paths still have to be absolute, and `create_host_path: false` stops docker making an empty directory when the source is missing, see [stack conventions](../conventions.md)
