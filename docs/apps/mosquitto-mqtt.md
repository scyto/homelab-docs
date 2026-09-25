---
title: "MQTT (mosquitto) swarm template"
source_gist: https://gist.github.com/scyto/650749b7297587e8c51be08c027d8b2c
---

# MQTT (mosquitto) swarm template

## Description
This template runs mqtt for use with home automation

## State Considerations for SWARM
Mosquitto 2 needs a config before it will listen on anything but localhost.
The config is `mosquitto.conf` in git. It deploys as a swarm config, which is available to the whole swarm, with a version in its name, see [stack conventions](../docker/conventions.md#swarm-configs-are-versioned-by-name).

## Network Considerations
none, this publishes the default port of 1883 (if you need port 9001 then you already know why and how to modify this example :-) )

## Placement Considerations
None, this runs a single replica.
This is for home network so no additional scale or redundancy needed in my usecase.

--8<-- "blocks/swarm/mqtt/compose.yml.md"

The config looks like this :-)

--8<-- "blocks/swarm/mqtt/mosquitto.conf.md"
