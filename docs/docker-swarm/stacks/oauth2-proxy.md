---
title: "runs my oauth2-proxy for Azure based auth"
source_gist: https://gist.github.com/scyto/7315468af220655fea1fde7366d8c506
---

# runs my oauth2-proxy for Azure based auth

## Description
This template runs my ouath2-proxy for azure auth for web sites that don't have any native auth mechansim.

## State Considerations for SWARM
none, this container can be cofigured entirely by env vars so i use those

## Network Considerations
none, this published default port of 4180 for this container, it can be reached by swarmIP:4180

## Placement Considerations
None, by default this template will result in a single replica. 
This is for home network so no addtioanl scale or redundancy needed in my usecase.

```
version: "3"
services:
  oauth2-proxy:
    container_name: oauth2-proxy
    hostname: oauth2-proxy
    environment:
      - OAUTH2_PROXY_PASS_HOST_HEADER=true
      - OAUTH2_PROXY_REVERSE_PROXY=true
      - OAUTH2_PROXY_SKIP_PROVIDER_BUTTON=true
      - OAUTH2_PROXY_WHITELIST_DOMAIN=.mydomain.com  # use . for all
      - OAUTH2_PROXY_COOKIE_SECRET=redacted
      - OAUTH2_PROXY_EMAIL_DOMAINS=mydomain.com      # use . for all
      - OAUTH2_PROXY_CLIENT_ID=redacted
      - OAUTH2_PROXY_CLIENT_SECRET=redacted
      - OAUTH2_PROXY_PROVIDER_DISPLAY_NAME='your email' #no really leave as your email, this is a UI hint only
      - OAUTH2_PROXY_HTTP_ADDRESS=http://0.0.0.0:4180
      - OAUTH2_PROXY_PROVIDER=azure

    image: quay.io/oauth2-proxy/oauth2-proxy
    ports:
      - 4180:4180/tcp
    restart: always
    ```
