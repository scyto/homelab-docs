---
title: "Home Assistant: Configuration"
---

# configuration

most of the configuration lives in the ui and is stored in `.storage/`. what is
left in yaml is short, and all of it is here.

## files in `/config`

| file | what it is |
| --- | --- |
| `configuration.yaml` | the top level, below |
| `automations.yaml` | written by the automation editor, never by hand |
| `scenes.yaml` | written by the scene editor |
| `scripts.yaml` | empty, there are no scripts |
| `alexa.yaml` | the alexa smart home skill |
| `light.yaml` | light groups |
| `packages/` | packaged yaml, all of it currently disabled by its file name |
| `secrets.yaml` | every credential the yaml uses. never published |
| `esphome/` | the [esphome](esphome.md) device configs |
| `blueprints/` | blueprints, below |

## configuration.yaml

```yaml title="configuration.yaml"
#########################################################################
###                                                                   ###
###       core home assistant stuff aka not device integrations       ###
###                                                                   ###
#########################################################################
# Configure a default setup of Home Assistant (frontend, api, etc)
default_config:

# !includes
automation: !include automations.yaml
script:     !include scripts.yaml
scene:      !include scenes.yaml

# alexa automation
alexa: !include alexa.yaml


#########################################################################
###                                                                   ###
###                      devices start here                           ###
###                                                                   ###
#########################################################################

# !includes
# this includes genmon sensor config and keymaster automations

homeassistant:
  packages: !include_dir_named packages

# convert switches to lights and create some light groups
light: !include light.yaml
```

## alexa

the smart home skill exposes four domains to alexa. the client id and secret are
from the skill's account linking, and come from `secrets.yaml`.

```yaml title="alexa.yaml"
smart_home:
  locale: en-US
  endpoint: https://api.amazonalexa.com/v3/events
  client_id: !secret alexa_client_id
  client_secret: !secret alexa_client_secret
  filter:
    include_domains:
      - light
      - climate
      - lock
      - switch
```

## light groups

two groups of insteon dimmers, so a room switches as one light.

```yaml title="light.yaml"
- platform: group
  name: Living Room Lights
  entities:
    - light.living_room_cans
    - light.living_room_edge_spots
    - light.living_room_sconces


- platform: group
  name: All Master Bedroom Dimmers
  entities:
    - light.master_bedroom_sconces
    - light.master_bedroom_cans
    - light.master_bed_lone_can
```

## alarm panel

none at the moment. the dsc panel's envisalink 3 and its yaml were removed on
2026-10-06; an eyezon uno will replace it, set up in the ui with the
`envisalink_new` custom integration rather than yaml.

## packages

`packages:` loads every `*.yaml` under `packages/`, one package per file. both
files there are switched off by their extension, so nothing loads today:

- `genmon/genmon.yaml.ignore`: sensors for the generator, read from genmon
- `additional_yaml/zwave_js.yaml.disabled`: left from before z-wave js was set
  up in the ui

## blueprints

automation blueprints, by author folder: CyanAutomation, HASwitchPlate,
Konstigt, TJ-developer, TurtleFX, bbbenji, dirkk1980, fxlt, gregmac, hunterjm,
kevinxw, networkingcat, and the ones home assistant ships. five automations use
one: lights on at sunset (CyanAutomation), both leak notifiers (bbbenji,
TurtleFX) and both certificate renewals (Konstigt).

## automations

twelve, all written in the editor:

| automation | does |
| --- | --- |
| Lights On At Sunset | porch lights at sunset (blueprint) |
| Turn Off Front Porch Lights at Sunrise | and off again |
| toggle wetbar insteon device on | keeps a z-wave rgbw strip on and awake |
| Water Detection & Shutoff | any leak sensor wet: notify and close the [flo](integrations.md) valve |
| Leak detection & notifier, Leak detection & notification 2 | push a leak to the phones (blueprints) |
| renew ha cert, renew homeassistant cert | renew the two certificates home assistant serves when their cert expiry sensors say so, checked at 04:00 (blueprint) |
| Keep the OpenThread border router running, Alert when the OpenThread border router add-on stays stopped | restart the otbr add-on, and say so if it will not stay up |
| HVAC: alert when the thermostat stops reporting | no status from the thermostat for an hour, or a zone unavailable for an hour: push and a persistent notification |
| zwavejs_lock_update | from the zwavejs2mqtt days: polls the front deadbolt's lock mode over mqtt |
