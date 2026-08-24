---
title: "infinitude for Carrier Infinity Thermostats (and Bryant)"
source_gist: https://gist.github.com/scyto/c66a053477b05552ef9f33fb1abed4a2
---

# infinitude for Carrier Infinity Thermostats (and Bryant)

## Description
This template runs my infinitude proxy instance.  This enables Carrier Inifinity Thermostats to be controlled by API, web page, home assistant etc)
One note please for the love of god never buy a carrier heating system with one of these controls they are terrible in my experience.  I inherited it, instead buy a nice generic heating/AC system that can support any standard thermostat.

## State Considerations for SWARM
none, this container can be cofigured entirely by env vars so i use those

## Network Considerations
none, this published port of 4000 for this container oveeride the interall 3000 because i have container that needed 3000
it can be reached by swarmIP:4000


## Placement Considerations
None, by default this template will result in a single replica. 

```
version: "3"
services:
  infinitude:
    environment:
      - PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
      - LANG=en_US.UTF-8
      - LANGUAGE=en_US:en
      - LC_ALL=en_US.UTF-8
      - APP_SECRET=Pogotudinal
      - PASS_REQS=600
      - MODE=Production
      - SERIAL_TTY=
      - SERIAL_SOCKET=192.168.1.47:23 # this connects to a RS484 > IP convertor, it lets me read the CAN bus of the thermostat for entertainment purposes.
    hostname: infinitude
    image: scyto/infinitude:latest #this is one container of my own making, if you have a carrier infinity thermostat please feel free to give it a go!
    ports:
      - 4000:3000/tcp
    restart: always
    stdin_open: true
    tty: true
```
