---
title: "Home Assistant: ESPHome"
---

# esphome

the devices i build myself, compiled and flashed by the ESPHome Device Builder
add-on. the configs are in `/config/esphome/`, and the wifi credentials come
from its own `secrets.yaml`.

| config | device | board | does |
| --- | --- | --- | --- |
| `respeaker.yaml` | respeaker-lite | Seeed ReSpeaker Lite, esp32-s3 | a voice satellite for assist: wake word, mics, speaker, mute switches |
| `sensors1.yaml` | sensors1 | Adafruit Feather ESP32 | air quality, with a Sensirion SPS30 particulate sensor |
| `grilltemp.yaml` | grilltemp | NodeMCU (esp8266) | the grill's temperature, from a MAX31856 thermocouple board |
| `tommy-4.yaml` | esp05 | esp32 | a TOMMY wifi motion sensing node, from `github://tommy-sense/esphome` |

`esphome/archive/` keeps old configs that are no longer flashed.
