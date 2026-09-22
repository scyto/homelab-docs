---
title: "The Arr Stack"
---

# the arr stack

ten containers as one portainer stack on [truenas1](../docker/standalone/truenas1.md), deployed from git like everything else.

| app | does | port |
| --- | --- | --- |
| prowlarr | indexer manager, feeds the others | 9696 |
| sonarr | tv series | 8989 |
| radarr | films | 7878 |
| bazarr | subtitles for sonarr and radarr | 6767 |
| profilarr | quality profiles for sonarr and radarr | 6868 |
| seerr | requests | 5055 |
| jellyfin | media server | 8096 |
| flaresolverr | solves indexer challenges for prowlarr | 8191 |
| qbittorrent | torrent client, behind its own VPN | 8080 |
| sabnzbd | usenet client, behind its own VPN | 8081 |

## why a stack and not truenas apps

all ten are in the truenas community catalogue, but the two download clients need a VPN, and the catalogue can't express it: the app definitions fix the image and offer no capabilities or sysctls. so the whole set is one stack. splitting them would put each catalogue app on its own network, and they talk to each other by container name.

## one network

every service is on one bridge, `arrstack`, and they address each other by name: `sonarr:8989`, `radarr:7878`, `prowlarr:9696`. a service missing the `networks:` key lands on the project's default network instead, can't resolve the others, and still reports healthy.

## the download clients' VPN

qbittorrent and sabnzbd use hotio images with a wireguard client built in:

```yaml
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
      - net.ipv6.conf.all.disable_ipv6=1
    environment:
      - VPN_ENABLED=true
      - VPN_CONF=wg0
      - VPN_PROVIDER=generic
      - VPN_LAN_NETWORK=192.168.1.0/24,10.8.0.0/24
```

- the wireguard config is `wg0.conf` in each client's config directory on the host, not in git
- `VPN_LAN_NETWORK` is what's still reachable outside the tunnel, so the lan can use the web UI
- qbittorrent has `VPN_AUTO_PORT_FORWARD` on, sabnzbd doesn't need it

## storage

| path | holds |
| --- | --- |
| `/mnt/fast/configs/<app>` | each app's config and database, on the fast pool, covered by one recursive [snapshot task](../truenas/tasks-and-scripts.md#snapshots) |
| `/mnt/rust/media` | the library and downloads, one mount shared by every app that moves files, so a move is a rename, not a copy |

the apps that write to the library run as uid/gid 568, truenas's `apps` user (`PUID`/`PGID`, or `user:` for seerr), so they can all read and write the same files.

## dashboard

the apps carry homepage labels, and most have a widget. api keys and the qbittorrent password come from files, never the labels, see [homepage](../monitoring/homepage.md#widgets-and-their-keys). qbittorrent bans an address after five failed logins for an hour, and the dashboard's address is its swarm node's, so a wrong password there locks the dashboard out.
