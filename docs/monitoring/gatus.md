---
title: "Gatus"
---

# gatus health checks

[gatus](https://github.com/TwiN/gatus) runs every health check, on the swarm, UI on port `8085`. it replaced uptime kuma because its config lives in git.

## config in git

gatus reads its config straight from a checkout of the repo, which a [git-sync](https://github.com/kubernetes/git-sync) sidecar in the same stack keeps current:

- git-sync polls `deploy/swarm/gatus` every 60 seconds, over ssh, with a read-only deploy key held as a docker secret and github's host key pinned
- gatus reads `GATUS_CONFIG_PATH=/git/repo/stacks/swarm/gatus/config` and reloads when a file changes, so a merged check is live within a minute or two and nothing restarts
- `skip-invalid-config-update: true` keeps the last good config running if a change doesn't parse

the checks are split by what they cover:

| file | covers |
| --- | --- |
| `10-network.yaml` | the gateway and both adguards |
| `20-proxmox.yaml` | the nodes, cluster quorum, and glances on each node |
| `30-swarm.yaml` | the swarm nodes, the VIP, and the swarm's web services |
| `40-truenas.yaml` | truenas1 and its apps |
| `50-plumbing.yaml` | everything on the dashboard's plumbing tab |
| `60-hosts.yaml` | syn02 and pi-zwave01 |

### the sidecar

every stack that reads config from git carries its own git-sync sidecar, so changing one consumer never touches another. this is gatus's:

```yaml
services:
  git-sync:
    image: registry.k8s.io/git-sync/git-sync:v4.7.1
    user: "1000:1000"
    environment:
      - GITSYNC_REPO=git@github.com:<you>/<repo>.git
      - GITSYNC_REF=deploy/swarm/gatus
      - GITSYNC_PERIOD=60s
      - GITSYNC_ROOT=/git
      - GITSYNC_LINK=repo
      - GITSYNC_SSH_KEY_FILE=/dev/shm/key
      - GITSYNC_SSH_KNOWN_HOSTS_FILE=/known_hosts
      - GITSYNC_ADD_USER=true
      - GITSYNC_FILTER=blob:none
      - GITSYNC_SPARSE_CHECKOUT_FILE=/sparse-checkout
      - GITSYNC_HTTP_BIND=:8080
    entrypoint:
      - /bin/sh
      - -c
      - |
        umask 077
        printf '%s\n' "$$(cat /run/secrets/gitsync_ssh_key)" > /dev/shm/key
        [ -s /dev/shm/key ] || { echo "cannot write the ssh key" >&2; exit 1; }
        mkdir -p /tmp/.ssh && cp /ssh_config /tmp/.ssh/config || exit 1
        exec /git-sync
    volumes:
      - type: volume
        source: gitrepo
        target: /git
        volume:
          nocopy: true
    configs:
      - source: known_hosts
        target: /known_hosts
      - source: ssh_config
        target: /ssh_config
      - source: sparse_checkout
        target: /sparse-checkout
    secrets:
      - gitsync_ssh_key
    networks:
      discovery:
        aliases:
          - gatus-git-sync
```

`sparse-checkout`, every parent listed:

```
/*
!/*/
/stacks/
!/stacks/*/
/stacks/swarm/
!/stacks/swarm/*/
/stacks/swarm/gatus/
!/stacks/swarm/gatus/*/
/stacks/swarm/gatus/config/
```

`ssh_config`:

```
Host github.com
  ConnectTimeout 15
  ServerAliveInterval 10
  ServerAliveCountMax 3
```

- **only the config folder is downloaded.** `blob:none` is a partial clone, commits and trees up front and file contents only for what's checked out, and the sparse checkout limits that to `config/`. about 200K on disk instead of the whole repo, and nothing else in the repo lands on the shared storage
- **the patterns have to list every parent.** git-sync turns on git's cone mode, which ignores a bare folder path: `/stacks/swarm/gatus/config/` on its own checks out the top level files and no config folder, and gatus starts with nothing to check and looks healthy. no comments in that file either
- **ssh gets its own timeouts.** git-sync's sync timeout kills `git` but then waits on a stuck `ssh` underneath it, so a stalled connection hangs the sidecar. with these, ssh gives up after 15 seconds and git-sync fails and restarts
- **the key is rewritten into `/dev/shm`.** an openssh key must end with a newline, and my secret store strips trailing whitespace, so the entrypoint puts it back. `/dev/shm` is memory, so the key never hits a disk, and if the write fails the container stops with the reason instead of starting without a key
- **uid 1000 needs `GITSYNC_ADD_USER` and `nocopy`.** ssh won't run for a uid with no passwd entry, and without `nocopy` docker seeds an empty volume with the image's `/git`, ownership included
- **`:8080` is its health.** it answers 5xx until the first sync, and git-sync exits on any failed sync, so one that keeps failing never answers 200. gatus checks it by the alias on the overlay, `http://gatus-git-sync:8080/`

## a fork, for one secret

the proxmox quorum check needs an api token. upstream gatus only substitutes environment variables into its config, and a token in an environment variable is readable by anything that can read the service. i run a small fork that also reads `PROXMOX_TOKEN_FILE`, a docker secret, and substitutes `${PROXMOX_TOKEN}` from it.

## checks prove it works, not that it answers

a 200 from a web server says little. each check asserts something only a working service returns:

| check | asserts |
| --- | --- |
| oauth2-proxy | `/ping` returns the body `OK` |
| frigate cameras | every camera in `/api/stats` reports `camera_fps > 0` |
| glances, every host | `/api/4/quicklook` returns collected memory, `mem > 0` |
| proxmox | an authenticated `cluster/status` says the cluster is quorate |

## checking a job by its result

some services have no port: they wake, do a job and sleep. those are checked by what the job produces.

| service | checked by |
| --- | --- |
| cloudflare ddns | a name that is a CNAME to the DDNS record answers over TLS, with a valid certificate only my proxy holds |
| acme.sh, BMC and synology | the certificate each device serves verifies for its hostname and has more than 21 days left |
| auto-label nodes | the node labels it maintains are present, read through the docker socket proxy |

```yaml
  - name: acme synology
    group: plumbing
    url: "https://syn02.mydomain.com:5101/"
    interval: 1h
    conditions: ["[CERTIFICATE_EXPIRATION] > 504h"]
```

by hostname with verification on, so a device that fell back to a self-signed certificate fails the check rather than passing on its long expiry.

## checking a database through the app that uses it

the databases are only on their own stack's network. rather than join gatus to each one, the check goes through the app:

| database | checked through |
| --- | --- |
| npm's mariadb | NPM's `/api/`, which queries it on every call |
| wordpress's mysql | `/wp-json/`, which reads the site's options table |
| open webui's redis | open webui's `/ready`, which pings redis |

## two traps when checking per node

- **address nodes by their own IP, never the VIP.** keepalived's VIP moves, so a check against it stays green while a node is down
- **macvlan.** a container can't reach a macvlan container on the same host, so gatus is kept off the two adguard nodes with placement constraints on the labels [auto-label](../apps/auto-label-nodes.md) maintains:

    ```yaml
          placement:
            constraints:
              - node.labels.running_adguard1 == 0
              - node.labels.running_adguard2 == 0
    ```

## small things

- endpoint keys are `<group>_<name>` with spaces turned into hyphens and nothing else escaped, so names stay free of brackets. the [dashboard](homepage.md) reads results by key
- `resolve-successful-conditions: true` on each endpoint shows the value a passing condition saw, not just the condition
- before relying on a new check, i break it on purpose and confirm it fails
