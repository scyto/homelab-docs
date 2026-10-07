---
title: "infinitude for Carrier Infinity Thermostats (and Bryant)"
source_gist: https://gist.github.com/scyto/c66a053477b05552ef9f33fb1abed4a2
---

# infinitude for Carrier Infinity Thermostats (and Bryant)

## Description
- This template runs my infinitude proxy instance. This enables Carrier Infinity Thermostats to be controlled by API, web page, home assistant etc.
- One note please for the love of god never buy a carrier heating system with one of these controls they are terrible in my experience.  I inherited it, instead buy a nice generic heating/AC system that can support any standard thermostat.
- I run the upstream image [nebulous/infinitude](https://hub.docker.com/r/nebulous/infinitude), pinned by digest.

## State Considerations for SWARM
- `state` is a named bind of `/mnt/docker-cephFS/infinitude_state`, mounted
  at `/infinitude/state`, see
  [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts).
  it holds everything the thermostat has sent. without it the data went with the
  task whenever swarm moved it to another node, and the api returned nothing until
  the thermostat next pushed.
- create the directory before the first deploy, the stack will not start without it:

    ```bash
    sudo mkdir /mnt/docker-cephFS/infinitude_state
    ```

- the rest is configured by env vars, except `APP_SECRET`, which is a swarm secret. An entrypoint wrapper reads it at startup, see [secrets](../secrets/index.md#option-3-an-entrypoint-wrapper).

## Network Considerations
- This publishes port 4000 for the container's internal 3000, because i have a container that needs 3000.
- It can be reached by swarmIP:4000.

## Placement Considerations
None, by default this template will result in a single replica.

--8<-- "blocks/swarm/infinitude/compose.yml.md"
