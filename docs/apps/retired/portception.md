---
title: "Portception - deploying portainer with portainer in a swarm"
source_gist: https://gist.github.com/scyto/46fa1f8d1b73663dc6cce5d8b2a4826a
---

# Portception - deploying portainer with portainer in a swarm
## No one should be like scyto, no one should do this..... be prepared to see your portainer disappear in a puff of smoke if you get this wrong


### Prep
1. This assumes all nodes are manager nodes
2. This assumes you already have agents managed as s stack / swarm service via portainer (see my other not recommended stack)
3. this assumes you have the portainer bind mounts on some shared medium (ceph, gluster, NFS, SMB - if you run it on one of the last two don't blame me if it corrupts)
4. my suggestiton is get your non-managed portainer working with your shared storage before you go any further 
5. BACKUP ALL YOUR STACKS / SECRETS AND CONFIGS - WORST CASE YOU CAN RECREATE EVERY STACK / SECRET / CONFIG BY HAND FAIRLY QUICKLY

### Deployment
This is a little hard to explain.... you have you existing portainer container and then you will be spinning up this swarm service - portainer doesn't really that.

Also i did this over a year ago and its a little fuzzy oin what i did, i think i:

1. created the stack and made sure I had different service names
2. i think i started the stack but then stopped it just after creation
3. stopped the existing portainer service via the command line
4. then restarted the new service from the command line 
5. IIRC i had to adopt all the stacks as they were percieved to be orphaned (there is a UI option)
6.  - but tbh i can't really recall... i played around... it was painfull

### Example stack
This is mine, I use glutser, change volumes to match you environment

``` 
version: '3.2'

services:  
  portainer:
    image: portainer/portainer-ee:latest
    command: -H tcp://tasks.agent:9001 --tlsskipverify
    ports:
      - "9443:9443"
      - "9000:9000"
      - "8000:8000"
    volumes:
      - data:/data
    networks:
      - portainer
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints: [node.role == manager]

networks:
  portainer:
    driver: overlay
    attachable: true

volumes:
  data:
    driver: gluster-vol1
```
