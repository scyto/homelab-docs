---
title: "Standalone Hosts"
---

# standalone docker hosts

three hosts run plain docker, not swarm. each runs a portainer agent and is its own environment in portainer, and their stacks deploy from git exactly like the swarm's: one directory per stack, one `deploy/<host>/<stack>` branch each, see [stacks in git](../gitops-with-portainer.md).

| host | what it is |
| --- | --- |
| [truenas1](truenas1.md) | the NAS. the arr stack and frigate run here to sit next to its storage and accelerators |
| [syn02](syn02.md) | a synology NAS |
| [pi-zwave01](pi-zwave01.md) | a raspberry pi 4 with the usb radios plugged into it |

[adding a host](add-a-host.md) is an agent and an environment in portainer.

## how they differ from the swarm

- compose keys the swarm ignores work here: `container_name`, `restart`, `devices`, `network_mode: host`
- labels go under `labels`, not `deploy.labels`. there is no service spec to hang them on
- healthchecks are fine. docker only reports them on a standalone host, where swarm would kill and reschedule the task
- a comment-only change to the compose does not recreate the container, compose compares the resolved config. on the swarm it does
- bind paths still have to be absolute, and `create_host_path: false` stops docker making an empty directory when the source is missing, see [stack conventions](../conventions.md)
