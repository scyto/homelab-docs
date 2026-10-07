---
title: "Home Assistant: Integrations"
---

# integrations

about 70 integrations, set up in the ui. there is no alarm panel integration at the moment, see [alarm panel](configuration.md#alarm-panel). grouped by what they do, with the count
of entries where there is more than one.

## lights, switches and power

| integration | for |
| --- | --- |
| Universal Devices ISY994 | the insteon dimmers and keypads, through an ISY |
| Z-Wave JS | locks, leak sensors, outlets, power strips, porch lights, a siren. the controller is on the [pi](../raspberry-pi/index.md) |
| LIFX (10) | bulbs, one entry each |
| Tasmota | flashed plugs, over mqtt |
| Matter, Thread (2), OpenThread Border Router (2) | matter-over-thread sensors, and both [border routers](../thread/index.md) |
| Tuya | two plugs and a screen-sync light |
| Switch as X | a switch shown as a light |
| Group | porch lights |
| iPIXEL Color *(custom)* | a bluetooth led panel |

## climate, air and water

| integration | for |
| --- | --- |
| Infinitude Beyond *(custom)* | the carrier infinity thermostat, three zones, through [infinitude](../apps/infinitude.md) |
| Navien Water Heater *(custom)* | the water heater |
| Flo by Moen *(custom)* | water flow, pressure and the main shutoff valve |
| Leakbot *(custom)* | the leakbot pipe sensor |
| Mila *(custom)* | air purifiers |
| Airthings | radon and air quality |
| Netatmo | the weather station and indoor modules |
| Sub-Zero *(custom)* | the fridge and freezer |

## security and cameras

| integration | for |
| --- | --- |
| Frigate *(custom)* | cameras and object detection, from [frigate](../apps/frigate.md) |
| go2rtc | camera streams |
| Ring | the doorbell and chimes |
| keymaster (4) *(custom)* | pin codes and schedules on the four z-wave locks |
| MyQ | garage doors |

## people and phones

| integration | for |
| --- | --- |
| Mobile App (5) | the companion app on phones, an ipad and the wall tablets |
| iOS | push notifications to the apple devices |
| Fully Kiosk Browser | the study wall tablet |
| SleepIQ | the beds' sleep number |
| Battery Notes *(custom)* | battery type and replacement date for 39 devices |

## media and voice

| integration | for |
| --- | --- |
| Music Assistant | the speakers, all of them |
| Sonos | the sonos speakers |
| HEOS, Denon AVR | the denon receiver |
| Apple TV (4), Google Cast, LG webOS, Songpal (2) | tvs and streamers |
| Harmony (4) | harmony hubs, one per room |
| DLNA (renderers and servers), MPD (2) | media renderers and libraries |
| Wyoming (4) | whisper, piper and openwakeword for assist, and a satellite |
| ESPHome (5) | the [esphome](esphome.md) devices |
| Alexa | the smart home skill, from [`alexa.yaml`](configuration.md#alexa) |

## home, energy and the house itself

| integration | for |
| --- | --- |
| Opower | utility usage and cost |
| Electricity Maps (co2signal) | grid carbon intensity |
| Anker Solix *(custom)* | a portable power station |
| Network UPS Tools | the basement [ups](../ups/index.md), from truenas1's nut server |
| Litter-Robot | the litter boxes |
| Roomba (4) | the vacuums |
| Brother, IPP | the printer |
| Met.no, GDACS, Sun | weather, disaster alerts, sun position |

## infrastructure

| integration | for |
| --- | --- |
| Home Assistant Supervisor, Backup, Home Assistant Cloud | the os, its add-ons, backups, remote access |
| MQTT | the [mosquitto](../apps/mosquitto-mqtt.md) broker |
| HACS *(custom)* | custom integrations and cards |
| AdGuard Home | the dns filter, see [adguard](../apps/adguard.md) |
| Glances | the HA VM's own load, from the [glances add-on](add-ons.md) |
| Synology DSM (6), UniFi, UniFi Protect | the nas, the network and its cameras |
| Certificate Expiry (7) | the certificates i care about |
| Ping | a host that should be up |
| HomeKit Controller (4) | homekit devices |
| Channels DVR *(custom)* | recent recordings |

## custom components

everything marked *(custom)* is in `/config/custom_components`. HACS installed
most of them, but it only tracks some, so its list is not the whole set.

| | in use | installed, not set up |
| --- | --- | --- |
| tracked by HACS | Battery Notes, Flo by Moen, Frigate, HACS, HA-Mila, iPIXEL Color, keymaster, Leakbot, Sub-Zero | |
| not tracked by HACS | anker_solix, channels_dvr_recently_recorded, infinitude_beyond, navien_water_heater | alexa_media, azure_openai_conversation, bambu_lab, favicon, fontawesome, hass_agent_mediaplayer, hass_agent_notifier, monitor_docker, simpleicons, spotcast, uhoo |
