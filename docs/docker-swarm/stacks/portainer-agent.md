---
title: "migrate portainer agent to be managed by portainer"
source_gist: https://gist.github.com/scyto/c2f1dbe119cc742d220dc13b50689ec8
---

# migrate portainer agent to be managed by portainer

## Description
This template deploys the portainer agent via portainer.  I wanted a way to update the agent independently from the portainer web app.
This is not a supported deployment architecture by portainer (which makes it odd they have the agent template in templates, any hoo)

### DO NOT DO ANY OF THIS UNLESS YOU ARE PREPARED TO RESINTALL PORTAINER AND ITS AGENTS IF YOU GET ANY STEP WRONG YOU WILL BREAK PORTAINER 

## State Considerations for SWARM
none, this container can be cofigured entirely by the stack file

## Network Considerations
the agent and portainer need to be on the same network
to make that full deterministic i chose to create the network manually in the portainer in the UI
this makes the network 'external' to the stack

### DO NOT DELETE OR STOP OLD AGENTS UNTIL YOU KNOW NEW AGENTS WORK

i reccommend that you:
  1. make the new portainer network overlay
  2. you make it attachable
  3. you use the portainer UI to attach your running portainer web app service / container instance to this new network in addition to its default
  4. you deploy this stack
  5. you retarget the environment at these new agent and ensure you can access them
  6. you then remove the old agent service from the UI (but not the portainer stack or web app)
  7. you edit the original compose file to remove the agent lines AND change it to so the portainer instance now uses the new portainer external network
  8. then you take the plunge and redeploy the portainer compose from the command line 

Once this all up and running you should still have a working system, you may find stacks marked as orhpnaned, this is not an issue, just click on the stack and then click associate


## Placement Considerations
None, by default this template will result in the agent being deployed to all nodes


```
  agent:
    image: portainer/agent
    environment:
      AGENT_CLUSTER_ADDR: tasks.agent   # note this is important to remeber this is what you use for the agent address
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /var/lib/docker/volumes:/var/lib/docker/volumes
    ports:                             # by publishing these you can also connect to the agent using node ip address : port if needed
      - target: 9001
        published: 9001
        protocol: tcp
        mode: host
    networks:
      - portainer
    deploy:
      mode: global
      placement:
        constraints: [node.platform.os == linux]

networks:
  portainer:
    external: true
```
