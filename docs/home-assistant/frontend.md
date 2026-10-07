---
title: "Home Assistant: Frontend"
---

# frontend

## dashboards

| dashboard | what it is |
| --- | --- |
| Overview | the main one, fifteen views, below |
| Locks | made by keymaster's dashboard strategy: one card per lock and code slot |
| Map | the default map |

the Overview's views:

| view | type | holds |
| --- | --- | --- |
| main | masonry | clock, weather, and auto-entities lists |
| Master Bed, Guest Room, Study, Living Room, Kitchen & Dining, Basement, Garage | masonry | one per room, mostly vertical stacks |
| Security | masonry | the default view: locks and cameras |
| Lighting | masonry | every light, from auto-entities |
| Battery Status | masonry | battery-state-card over every battery |
| Server | masonry | the printer and the two synology nases, as glance and gauge cards |
| Cat Room | sections | cameras, tiles and the thermostat |
| Water | sections | an auto-entities list |
| zzz | masonry | a scratch view: climate, media and camera cards |

## custom cards

loaded as dashboard resources from `/hacsfiles/` (HACS) or `/local/` (`www/`).
as with the integrations, HACS only tracks some of them.

| card | used for |
| --- | --- |
| Mushroom | climate, media and vacuum cards |
| auto-entities, card-tools, fold-entity-row, multiple-entity-row, slider-entity-row | building lists from filters, and richer rows |
| button-card | custom buttons |
| card-mod | styling cards |
| mini-graph-card, mini-climate-card, climate-mode-entity-row | graphs and thermostats |
| battery-state-card | the battery view |
| Advanced Camera Card (was Frigate card), surveillance-card | cameras |
| vertical-stack-in-card, stack-in-card | stacks without the gaps |
| weather-card, simple-clock-card | the main view |
| numberbox-card, rgb-light-card, badge-card | controls |
| spotify-card | spotify |
| roomba-vacuum-card, xiaomi-vacuum-card, xiaomi-vacuum-map-card | vacuums |
| gui-sandbox | trying out card config |
| call-external-message-bus.js (`/local/`) | lets a card send a message to the companion app |
| keymaster.js | the Locks dashboard's strategy |

HACS tracks Advanced Camera Card, auto-entities, card-tools, fold-entity-row and
Number Box. the rest were installed before HACS tracked them, or by hand.
