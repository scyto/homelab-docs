---
title: "Home Assistant"
---

# home assistant

home assistant runs everything in the house that has a radio or an app: lights,
locks, leak sensors, the hvac, cameras, media, and the voice assistant. this
section records what is installed and how it is configured, so i can rebuild it.
it is an inventory, not a guide.

| | |
| --- | --- |
| install | Home Assistant OS 18.3, the `ova` image, as a VM on the [proxmox cluster](../proxmox/index.md) ([how it moved there](../proxmox/migration/home-assistant.md)) |
| core | 2026.10, on the **beta** update channel |
| disk | 125 GB, about 55 GB used. the recorder database is most of it |
| radios | z-wave, zigbee and thread live on the [pi](../raspberry-pi/index.md), not on the VM. thread has two border routers, see [thread](../thread/index.md) |

## pages

- [configuration](configuration.md): `configuration.yaml`, the yaml i wrote by
  hand, and the blueprints
- [integrations](integrations.md): every integration, and the custom ones
- [add-ons](add-ons.md): what runs beside core
- [frontend](frontend.md): dashboards and the custom cards
- [esphome](esphome.md): the devices i build myself

## how it fits together

- almost everything is configured in the ui. yaml is kept for the few things
  the ui cannot do, or could not when i set them up
- secrets live in `secrets.yaml` and are only ever referenced with `!secret`.
  nothing on these pages is copied from it
- devices that need a server of their own run it elsewhere and home assistant
  talks to it: the carrier thermostat goes through
  [infinitude](../apps/infinitude.md), cameras through
  [frigate](../apps/frigate.md), mqtt through
  [mosquitto](../apps/mosquitto-mqtt.md)
- i reach the config with the Advanced SSH and Studio Code Server add-ons, and
  claude reaches it through the Home Assistant MCP Server add-on
