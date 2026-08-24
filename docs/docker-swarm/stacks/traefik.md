---
title: "certificatesDuration: 72    # only use a short duration like this for testing"
source_gist: https://gist.github.com/scyto/1932a9e21c9b8030e8325ab3b380bdf7
---

## Description
This template runs my experimental traefik server for evaluating if i move to it from handcrafted nginx proxy.

## State Considerations for SWARM
traefik requires a static configuration - you need to pick either file based on command line based (or all commands need to be in your stack).
you cannot mix these - for example if you put some settigs in a file doing additonal static config via command line then things kike env vars will be ignored
i chose to put the static config in a traefik.yml file this seems to be considerd best practice in 2.6 by some
i also configured a dynamic files folder - this is for aything that can't or shouldn't be configured in a docker file (middlewares, non-docker related routers etc)

## Network Considerations
This need to publish all router endpoints and a port for the web interface.
Note: in a swarm the normal port detection function of the docker provider doesn't work and ports need to be explicitly published and the proxy port defined in the docker (like you see)

## Placement Considerations
None, by default this template will result in a single replica. 
This is for home network so no addtional scale or redundancy needed in my usecase.

stack file:

```
version: "3.3"

services:
  traefik:
    image: "traefik:latest"
    restart: always 
    ports:                                  #these 3 ports must be published (8080 is for the dashboard reverse proxy)
      - "80:80"
      - "443:443"
      - "8081:8080"
    networks:
      - traefik-public
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - data:/data                          # i user glusterfs plugin volume driver instead of regaulr bind mounts this is where my dynamic files live
    configs:                                # i use configs to store the static config and make available to entire swarm cluster
      - source: traefik_config
        target: /etc/traefik/traefik.yml
    environment:
      - CF_DNS_API_TOKEN=redacted  #CF DNS key for ACME (letsencrypt DNS challenge)
      labels:
        - "traefik.enable=true"
        #Traefik Router Setup  - the auth files are optional
        - "traefik.http.routers.traefik.rule=Host(`traefik.mydomain.com`)"
        - "traefik.http.routers.traefik.service=api@internal"
        - "traefik.http.routers.traefik.entrypoints=https"
        # - "traefik.http.routers.traefik.middlewares=oauth2-redirect@file"     #i store my oauth details in file in the dynamic files location
        - "traefik.http.routers.traefik.middlewares=basic-auth@file"            #i store basic auth details in a file in the dynamic files location
        
        # Dashboard Service Setup
        - "traefik.http.services.dashboard.loadbalancer.server.port=8081" # this isn't really used but is required, in reality the port can be anything and the services.name can be anyting note 8081 must be published

        # global redirect to https
        - "traefik.http.routers.http-catchall.rule=hostregexp(`{host:.+}`)"
        - "traefik.http.routers.http-catchall.entrypoints=http"
        - "traefik.http.routers.http-catchall.middlewares=redirect-to-https"

        # middleware redirect
        - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"

configs:
  traefik_config:
    external: true

volumes:
  data:
    driver: gluster-vol1

networks:
  traefik-public:
```

Traefik docker swarm config - I used portainer to create and maintain this file, it is called in the stack above.

```
pilot:
    token: "redacted"

api:
  dashboard: true
  debug: true

log:
  level: FATAL

entryPoints:
  http:                           # i name my 80 and 443 entry points as http and https as i found 'websecure' very effing confusing in all the canonical examples
    address: ":80"
  https:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    swarmMode: true
    exposedByDefault: false
  file:
    directory: /data/sites-enabled       #this woukd be used to define sites to be proxied that are not part of docker, such as services running on another device etc
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:    
      email: email@mydomain.com
      storage: /data/acme.json
#      certificatesDuration: 72    # only use a short duration like this for testing
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
          - "9.9.9.9:53"
```

This is the basic auth file - i place this in the file provider location as it mean i can add/remove users without needed to restart the container

```
http:
  middlewares:
    basic-auth:
      basicAuth:
        users:
          - "username:htpasswd-hash"
```

at this time i am not posting my oauth2 config as i have yet to get this fully wokring with traefik
