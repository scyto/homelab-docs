---
title: "Auto Label"
source_gist: https://gist.github.com/scyto/642d9fa2b5392b14a5f989c9ff281e34
---

# Auto Label

This container puts a label on each machine based on a config that matches service names.
If the service is running on a node the label gets a 1, and if it isn't the label gets a 0.
this can be used with constraints to either locate services on a node with another service OR make sure a service doesn't land on a node with another service

I would love to find a better version of this that does this without the need for the manual config file (you can use a file bindmount instead of a config if you prefer)

## Swarm Consideration
State is all read-only in a config.
This runs as one replica on a manager and sets the labels on every node.
The config is `servicelist.txt` in git. It deploys as a swarm config with a version in its name, see [stack conventions](../docker/conventions.md#swarm-configs-are-versioned-by-name).

### Stack

--8<-- "blocks/swarm/autolabel/compose.yml.md"

### Config
This is the name of the service when running followed by what you want the label to say.
Use `sudo docker service ls` to get the names.

--8<-- "blocks/swarm/autolabel/servicelist.txt.md"

### How i use this with adguard to make sure adguard 1 and 2 don't run on the same node EVER (which causes failure conditions)

```
...
  adguard2:
    ...
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints: [node.labels.running_adguard1 == 0]
...
```
