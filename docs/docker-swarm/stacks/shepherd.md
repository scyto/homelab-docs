---
title: "shepherd swarm image updater"
source_gist: https://gist.github.com/scyto/1091c492fa0c8353be4cbfa3874c7f54
---

!!! warning "Deprecated: I no longer run this"

    Shepherd did the thing watchtower could not, which is update swarm
    *services*. It served me well for years.

    Two reasons it is gone. The image is from 2023 and cannot read OCI image
    manifests, so for a growing number of registries it silently could not tell
    whether an update existed. And like watchtower it changed what was running
    without touching the compose in git, which stopped making sense once the
    compose became the source of truth.

    Replaced by [Renovate](../image-updates-renovate.md).

    Kept for reference, and because the placement notes below are still a decent
    illustration of pinning a service to a manager node.

## Update Swarm Images ##
i wanted to update swarm images whenever there is a new image available (even at the risk of breaking something)

it seems watchtower can't do this for swarm stacks/services - only one off containers.

I found this great container from https://github.com/djmaze/shepherd  

### placement considerations

Must be placed on a manager node.

### Config notes
By default it will refresh all services, exclude any you dont want it to touch.
I am not using apprise for this yet, but will be implementin apprise soon.


```
version: "3"
services:
  shepherd:
    build: .
    image: mazzolino/shepherd
    environment:
      - SLEEP_TIME=60m
      - IGNORELIST_SERVICES="shepherd_shepherd wordpress_db wordpress_wordpress"
      - ROLLBACK_ON_FAILURE=true
      - TZ=America/Los_Angeles
      - IMAGE_AUTOCLEAN_LIMIT=2
#      - APPRISE_SIDECAR_URL=apprise-microservice:5000      	
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    deploy:
      placement:
        constraints:
        - node.role == manager
```
