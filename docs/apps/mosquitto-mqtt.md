---
title: "MQTT (mosquitto) swarm template"
source_gist: https://gist.github.com/scyto/650749b7297587e8c51be08c027d8b2c
---

# MQTT (mosquitto) swarm template

## Description
This template runs mqtt for use with home automation

## State Considerations for SWARM
With the latest version of mosquitto a single config is required to enable it to listen.
You can do this by mapping thevconfig in a volume mount as per normal.
However in this version i have implemented configs as these are available to the whole swarm

## Network Considerations
none, this published default port of 1883 (if you need port 9001 then you already know why and how to modify this example :-) )

## Placement Considerations
None, by default this template will result in a single replica. 
This is for home network so no addtioanl scale or redundancy needed in my usecase.

```
version: "3.8"

services:
  mosquitto:
    image: eclipse-mosquitto
    configs:
      - source: mqtt_config
        target: /mosquitto/config/mosquitto.conf

    ports:
      - 1883:1883

configs:
  mqtt_config:
    external: true
```

the data store in the cofig looks like this :-)
Use the portainer UI to create a config - note once created they cannot be edited (they have to be destroyed and recreated and configs in use by a stack cannot be deleted.  As such best used for config data you don't want to change very often.

```
listener 1883
allow_anonymous true
```
