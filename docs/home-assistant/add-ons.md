---
title: "Home Assistant: Add-ons"
---

# add-ons

what runs beside core on the VM. the supervisor calls them apps now.

| add-on | for |
| --- | --- |
| Advanced SSH & Web Terminal | a shell, and key-based ssh into `/config` |
| Studio Code Server | editing the yaml in a browser |
| Samba share | `/config` and backups as a windows share |
| Samba Backup | a full backup every night at 22:00, copied to a samba share |
| Home Assistant MCP Server | lets claude read and change home assistant. its read only mode is a switch in its settings |
| Glances | the VM's cpu, memory, disks and containers, for the Glances integration. `process_info` is off, so it lists no processes and no command lines |
| ESPHome Device Builder | builds and flashes the [esphome](esphome.md) devices |
| Network UPS Tools | a nut server on the VM. the ups integration reads truenas1's instead |
| Matter Server | matter |
| OpenThread Border Router | the first [thread border router](../thread/index.md), with its radio on the pi through ser2net |
| Whisper, Piper, openWakeWord | speech to text, text to speech, and wake word for assist |
| Assist Microphone | a usb microphone as an assist satellite |
| Music Assistant | the music server behind the speakers |
| YT Music PO Token Generator | lets music assistant play youtube music |
| Bluetooth Audio Manager (Dev) | bluetooth speakers for music assistant |
| TOMMY | wifi motion sensing, with the [esphome](esphome.md) tommy node |

installed but stopped: TasmoAdmin, Let's Encrypt, SQLite Web.
