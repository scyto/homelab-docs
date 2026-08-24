---
title: "- APPRISE_SIDECAR_URL=apprise-microservice:5000"
source_gist: https://gist.github.com/scyto/1091c492fa0c8353be4cbfa3874c7f54
---

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
