---
title: "Gatus"
---

# gatus health checks

[gatus](https://github.com/TwiN/gatus) runs every health check from the swarm, with its UI on port `8085`. it replaced uptime kuma because its config lives in git.

--8<-- "blocks/swarm/gatus/compose.yml.md"

## before you deploy

1. create both folders on the cephfs mount, and give `gatus_git_v2` to uid 1000, which git-sync runs as:

    ```
    sudo mkdir -p /mnt/docker-cephFS/gatus_git_v2 /mnt/docker-cephFS/gatus_data
    sudo chown 1000:1000 /mnt/docker-cephFS/gatus_git_v2
    ```

    - a missing folder fails the task, because each volume binds its folder by path

2. create the `discovery` overlay on a manager. the stack joins it and does not own it:

    ```
    docker network create -d overlay --attachable --scope swarm discovery
    ```

    - `discovery` belongs to no stack, so removing gatus never takes it away from homepage or the docker socket proxy

    gatus also joins `traefik-api`, where it reads traefik's API. create it as in [traefik's steps](../apps/traefik.md#before-you-deploy)

3. create the two docker secrets. `gitsync_ssh_key_v1` is the private half of a read-only deploy key on the repo, and `proxmox_api_token_v1` is the secret of the proxmox api token `pve-auditor@pam!homepage`

## state considerations

both volumes are named binds on cephfs, see [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts):

- `data`, from `/mnt/docker-cephFS/gatus_data`, holds the check history, a SQLite database, and the hourly copy [the fork](#the-fork) makes of it in `/data/backup/`
- `gitrepo_v2`, from `/mnt/docker-cephFS/gatus_git_v2`, holds git-sync's checkout. gatus mounts it read-only and reads its config from it

on cephfs, git-sync and gatus don't have to share a node, so gatus can move when a node goes down.

## network considerations

- gatus publishes its UI's `8080` as `8085` through the ingress mesh, so every swarm node and the keepalived VIP answer on it, `192.168.1.45:8085` included. its dashboard tile links to it by name, `https://gatus.mydomain.com`
- it joins `discovery` to reach the swarm's read-only docker socket proxy as `dockerproxy:2375`, which has no port on the lan. git-sync joins it too, as `gatus-git-sync`, so gatus's check reaches the sidecar's health endpoint by name
- it joins `traefik-api` to read traefik's API at `http://traefik_traefik:8080`, since `traefik.mydomain.com` is behind oauth

## config in git

gatus reads its config straight from a checkout of the repo, which a [git-sync](https://github.com/kubernetes/git-sync) sidecar in the same stack keeps current:

- gatus reads `GATUS_CONFIG_PATH=/git/repo/stacks/swarm/gatus/config` and reloads when a file changes, so a merged check is live within a minute or two and nothing restarts
- `skip-invalid-config-update: true` keeps the last good config running if a change doesn't parse

the checks are split by what they cover, one file each:

--8<-- "blocks/swarm/gatus/config/00-global.yaml.md"

--8<-- "blocks/swarm/gatus/config/10-network.yaml.md"

--8<-- "blocks/swarm/gatus/config/20-proxmox.yaml.md"

--8<-- "blocks/swarm/gatus/config/30-swarm.yaml.md"

--8<-- "blocks/swarm/gatus/config/40-truenas.yaml.md"

--8<-- "blocks/swarm/gatus/config/50-plumbing.yaml.md"

--8<-- "blocks/swarm/gatus/config/60-hosts.yaml.md"

--8<-- "blocks/swarm/gatus/config/80-ups.yaml.md"

<!-- the sidecar moved to docker/config-from-git.md. the empty span keeps
its old anchor working -->

<span id="the-sidecar"></span>the sidecar and gatus's `sparse-checkout`, `ssh_config` and `known_hosts` are on [config from git](../docker/config-from-git.md).

## the fork

i run a small fork, [scyto/gatus](https://github.com/scyto/gatus), for two things upstream doesn't do.

**a token from a file.** the proxmox quorum check needs an api token. upstream gatus only substitutes environment variables into its config, and a token in an environment variable is readable by anything that can read the service. the fork also reads `PROXMOX_TOKEN_FILE`, a docker secret, and substitutes `${PROXMOX_TOKEN}` from it.

**a backup of gatus's database.** the check history is SQLite in WAL mode, so a [cephfs snapshot](../backups/cephfs.md#databases) can catch it mid-write. nothing outside gatus can copy it safely: WAL needs every reader on the same host, swarm can't keep a sidecar on gatus's node, and the image has no shell. so the fork copies it with `VACUUM INTO` to `GATUS_SQLITE_BACKUP_PATH`, at start and hourly at :50.

## what each check asserts

each check asserts something only a working service returns, beyond a 200 from its web server:

| check | asserts |
| --- | --- |
| oauth2-proxy | `/ping` returns the body `OK` |
| frigate cameras | each camera the check names reports `camera_fps > 0` in `/api/stats` |
| glances, every host | `/api/4/quicklook` returns collected memory, `mem > 0` |
| proxmox | an authenticated `cluster/status` says the cluster is quorate |
| ups cards | each card's web server answers `/` itself, with its redirect not followed, see [below](#checking-the-ups-cards-and-nut) |
| nut data, every NUT server | prometheus holds that server's `OL` flag at `1`, scraped from the NUT exporter within the last minute, see [below](#checking-the-ups-cards-and-nut) |

## checking the proxy

gatus checks [traefik](../apps/traefik.md) in five ways, and never through an
address outside my lan:

- every route gets a check, generated with the routes. each goes through the
  VIP with the name as the Host header and no DNS, so one mis-wired route goes
  red on its own
- traefik itself is checked by reading its API over `traefik-api`, with no name
  and no DNS
- one check goes by name, to `auth.mydomain.com/ping`, the one name with no
  sign-in in front. it covers DNS, the VIP, traefik and the certificate
- an app behind oauth also gets a check on its own address. its route check
  only reaches the sign-in, which answers with a redirect whether the app is
  up or not
- a name outside my domain has a certificate of its own, which the route
  checks can't see. it gets a check by name, for the certificate's expiry,
  and gatus's `extra_hosts` points that name at the VIP, so the check stays on
  the lan

## checking a job by its result

some services have no port: they wake, do a job and sleep. gatus checks those by what the job produces.

| service | checked by |
| --- | --- |
| cloudflare ddns | the DDNS record, resolved through a public resolver because my lan has its own copy of that name, answers over TLS with a valid certificate only my proxy holds |
| acme.sh, BMC and synology | the certificate each device serves verifies for its hostname and has more than 21 days left |
| auto-label nodes | the node labels it maintains are present, read through the docker socket proxy |

## checking a database through the app that uses it

the databases are only on their own stack's network. gatus joins none of those networks and checks each database through its app:

| database | checked through |
| --- | --- |
| wordpress's mysql | `/wp-json/`, which reads the site's options table |
| open webui's redis | open webui's `/ready`, which pings redis |

## checking the UPS cards and NUT

the [UPS](../ups/index.md) cards, the NUT servers that read them, and the data
those servers hold each get a check of their own, because they fail
separately:

- each card's web server gets a GET to `/`. the card answers `303` to its login
  page, and gatus follows redirects by default, so the check sets
  `client.ignore-redirect: true` and asserts the card's own answer:

    ```yaml title="swarm/gatus/config/80-ups.yaml"
      - name: ups card study
        group: ups
        url: "http://192.168.1.73/"
        client:
          ignore-redirect: true
        conditions:
          - "[CONNECTED] == true"
          - "[STATUS] < 400"
    ```

    - this is the check that catches a hung card. a card can hang with its
      switch port up, so nothing on the network notices

- the three NUT servers with readers, truenas1's, pve1's and the
  [smc closet stack's](../ups/smc.md) on `3494`, get a TCP connect:

    ```yaml title="swarm/gatus/config/80-ups.yaml"
      - name: nut pve1
        group: ups
        url: "tcp://192.168.1.81:3493"
        conditions: ["[CONNECTED] == true"]
    ```

    - a connect proves the server is up, not that its data is fresh. `upsd`
      keeps accepting connections when its driver has lost the card, and says
      so as `DATA-STALE` over the NUT protocol, which gatus can't speak. what
      the connect is for is telling a server that is gone from a server with
      nothing fresh to say

- every NUT server's data is judged by what prometheus has from it, the way
  [unpoller](unpoller.md#check-it-works) is. truenas1 runs the NUT exporter
  from the [prometheus-exporters sysext](../truenas/sysexts.md), which reads a
  NUT server over the NUT protocol on every scrape, and prometheus scrapes it
  once a minute, [one job per server](../ups/proxmox.md#prometheus). the smc
  closet's stack carries [its own exporter](../ups/smc.md#prometheus), because
  the sysext's ignores the port it is given. the check
  asks prometheus for that server's `OL` flag and wants exactly `1`:

    ```yaml title="swarm/gatus/config/80-ups.yaml"
      - name: nut data pve2
        group: ups
        url: "http://192.168.1.86:30104/api/v1/query?query=network_ups_tools_ups_status%7Bups%3D%22ups-proxmox%22%2Cnode%3D%22pve2%22%2Cflag%3D%22OL%22%7D%20and%20%28time%28%29%20-%20timestamp%28network_ups_tools_ups_status%7Bups%3D%22ups-proxmox%22%2Cnode%3D%22pve2%22%2Cflag%3D%22OL%22%7D%29%29%20%3C%20150"
        conditions:
          - "[STATUS] == 200"
          - "[BODY].status == success"
          - "[BODY].data.result[0].value[1] == 1"
    ```

    - the query is `network_ups_tools_ups_status{ups="ups-proxmox",node="pve2",flag="OL"}`
      joined with `and (time() - timestamp(...)) < 150`, URL-encoded. the
      exporter adds no label saying which server a series came from, so each
      prometheus job adds `ups` and `node`. the age test turns a prometheus
      that has stopped scraping red: a bare selector keeps answering with its
      last sample for five minutes
    - green proves three things at once: that server's driver has fresh data
      from the card, the exporter reached the server, and prometheus scraped
      the exporter
    - a server whose driver has lost the card answers the exporter with
      `DATA-STALE`, the exporter fails the scrape with a `500`, prometheus marks
      the series stale on that first failed scrape, and the query returns an
      empty result. `result[0]` doesn't exist, so the check goes red
    - on battery `OL` is `0` and the check goes red. that is wanted: a power
      cut is the alert. the tooltip shows the value seen, so `0` is a power
      cut and `(INVALID)` is nothing fresh to read
    - every proxmox node gets one, not only pve1, because each node shuts
      itself down from its own driver. a stale driver on pve2 alone would
      leave pve2 without its warning while pve1 looked fine

## checking per node

- address nodes by their own IP, never the VIP. keepalived's VIP moves, so a check against it stays green while a node is down
- the adguards are macvlan containers, which a container on the same host can't reach. a shim on every swarm node covers their two IPv4 addresses only, so gatus runs on any node and checks them over IPv4. the shim is in [troubleshooting](../docker/troubleshooting.md#a-container-cant-reach-a-macvlan-container-on-the-same-host)

## small things

- endpoint keys are `<group>_<name>` with spaces turned into hyphens and nothing else escaped, so names stay free of brackets. the [dashboard](homepage.md) reads results by key
- `resolve-successful-conditions: true` under each endpoint's `ui:` shows the value a passing condition saw, as well as the condition
- before relying on a new check, i break it and confirm it fails

## checking it

this prints the key of every check whose latest result failed:

```
curl -s 'http://192.168.1.45:8085/api/v1/endpoints/statuses?page=1&pageSize=1' | jq -r '.[] | select(.results[0].success | not) | .key'
```

no output means every check passed.
