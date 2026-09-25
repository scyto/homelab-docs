---
title: "The Arr Stack"
---

# the arr stack

the arr stack is ten containers that portainer deploys from git as one stack on
[truenas1](../docker/standalone/truenas1.md): the arr apps, jellyfin, and two
download clients that send their traffic through a VPN. it is a stack because
the truenas catalog can't give the download clients their VPN.

--8<-- "blocks/truenas1/arrstack/compose.yml.md"

## before you deploy

1. create a config folder under `/mnt/fast/configs/` for each app except
   flaresolverr, which keeps nothing. seerr runs as uid 568, so give its folder
   to 568:

    ```
    sudo mkdir -p /mnt/fast/configs/{prowlarr,radarr,sonarr,bazarr,jellyfin,seerr,profilarr,qbittorrent,sabnzbd}
    sudo chown -R 568:568 /mnt/fast/configs/seerr
    ```

    - the binds are plain, so docker creates a missing folder empty and owned
      by root, and the app starts against it with no error. seerr can't write
      to a folder owned by root
    - the library, `/mnt/rust/media`, has to exist as well, writable by uid 568

2. put each download client's wireguard config at `wireguard/wg0.conf` in its
   config folder: `/mnt/fast/configs/qbittorrent/wireguard/wg0.conf` and
   `/mnt/fast/configs/sabnzbd/wireguard/wg0.conf`

    - it holds the tunnel's private key, so it is not in git and the compose
      can't carry it

3. before this stack starts, put qbittorrent's web UI password in homepage's
   key file, `homepage_config/secrets/qbittorrent_password`. see
   [homepage's steps](../monitoring/homepage.md#before-you-deploy)

    - homepage logs in on every refresh, and qbittorrent bans an address for an
      hour after five failed logins. homepage's address is its swarm node's, so
      a wrong password locks homepage out

## the apps

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

all ten are in the truenas community catalog, but the catalog can't express
the download clients' VPN: the app definitions fix the image and offer no
capabilities or sysctls. the apps talk to each other by container name, and
splitting them would put each catalog app on a separate network, so the whole
set is one stack.

## one network

every service is on one bridge, `arrstack`, and they address each other by
name: `sonarr:8989`, `radarr:7878`, `prowlarr:9696`. a service missing the
`networks:` key lands on the project's default network instead. it can't
resolve the others, and it still reports healthy.

## the download clients' VPN

qbittorrent and sabnzbd use hotio images with a wireguard client built in:

```yaml title="compose.yml"
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
      - VPN_LAN_LEAK_ENABLED=false
```

- `VPN_LAN_NETWORK` lists what stays reachable outside the tunnel, so the lan
  can use the web UI. with `VPN_LAN_LEAK_ENABLED=false`, nothing else leaves
  for the lan
- the web UI answers with the tunnel down, so both healthchecks fail when
  wireguard's last handshake on `wg0` is missing or older than 5 minutes.
  docker doesn't act on a standalone container's health, so an unhealthy client
  keeps running

## storage

| path | holds |
| --- | --- |
| `/mnt/fast/configs/<app>` | each app's config and database, on the fast pool, covered by one recursive [snapshot task](../truenas/tasks-and-scripts.md#snapshots) |
| `/mnt/rust/media` | the library and downloads, one mount shared by every app that moves files, so a move is a rename, not a copy |

sonarr, radarr, bazarr, jellyfin, qbittorrent and sabnzbd write to the library.
they run as uid and gid 568, truenas's `apps` user, set with `PUID` and `PGID`,
so they can all read and write the same files.

## dashboard

the apps carry homepage labels, and most have a widget. truenas1 runs plain
containers, so the labels sit under `labels:`. swarm stacks put theirs under
`deploy.labels`. api keys and the qbittorrent password come from files, never
the labels, see [homepage](../monitoring/homepage.md#widgets-and-their-keys).

## checking it

sonarr, radarr and prowlarr each answer `/ping`:

```
curl -s http://192.168.1.86:8989/ping http://192.168.1.86:7878/ping http://192.168.1.86:9696/ping | jq -r .status
```

```text
OK
OK
OK
```

and jellyfin answers `/health`:

```
curl -s http://192.168.1.86:8096/health
```

```text
Healthy
```

[gatus](../monitoring/gatus.md) runs these four checks every two minutes. for
qbittorrent and sabnzbd the check is their healthcheck, which also tests the
tunnel, see [the download clients' VPN](#the-download-clients-vpn).
