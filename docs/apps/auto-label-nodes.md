---
title: "Auto Label"
source_gist: https://gist.github.com/scyto/642d9fa2b5392b14a5f989c9ff281e34
---

# Auto Label

This container puts a label on each machine based on a config that matches service names.
If the service is running the label gets a 1 and if the label get as 0 its not running.
this can be used with constraints to either locate serices on a node with another service OR make sure a service doesn't land on a node with another service

I would love to find a better version of this that does this without the need for the manual config file (you can use a file bindmount instead of a config if you prefer)

## Swarm Consideration
State is all read-only in a config
You need this to run on all nodes.

### Example Stack
```
version: "3.7"
services:
  dockerautolabel:
    build: .
    image: davideshay/dockerautolabel:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    configs:
      - source: dockerautolabel_config
        target: /config/servicelist.txt
    deploy:
      mode: replicated
      replicas: 1    
      placement:
        constraints: [ node.role == manager]

configs:
  dockerautolabel_config:
    external: true
    
```

### Example Config (this is my real one as of writing this)
This is the name of the service when running followed by what you want the label to say
use `sudo docker service ls` to get the names 

```
adguard_adguard1,running_adguard1
adguard_adguard2,running_adguard2
adguard_adguardhome-sync,running_adguardhome-sync
agent_agent,running_agent
apprise_apprise-api,running_apprise-api
cloudflare-ddns_cloudflare-ddns,running_cloudflare-ddns
cluodflared_portainer-tunnel,running_portainer-tunnel
dockerproxy_dockerproxy,running_dockerproxy
infinitude_infinitude,running_infinitude
mqtt_mosquitto,running_mosquitto
npm_app,running_npm
npm_db,running_npm_db
oauth_oauth2-proxy,running_oauth2-proxy
portainer_portainer,running_portainer
shepherd_shepherd,running_shepherd
swag_swag,running_swag
unifiapibrowser_unifiapibrowser,running_unifiapibrowser
watchtower_watchtower,running_watchtower
wordpress_db,running_wordpress_db
wordpress_wordpress,running_wordpress
```

### Example of how i use this with adguard to make sure adguard 1 and 2 don't run on the same node EVER (which causes failure conditions)

```
...
adguard2:
    image: 'adguard/adguardhome:latest'
    restart: always
    volumes:
      - work2:/opt/adguardhome/work
      - config2:/opt/adguardhome/conf
    networks:
      - adguard2-mvl
      - adguard_sync
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints: [node.labels.running_adguard1 == 0]
        
...
```
