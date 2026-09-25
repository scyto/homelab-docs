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

3. create the two docker secrets. `gitsync_ssh_key_v1` is the private half of a read-only deploy key on the repo, and `proxmox_api_token_v1` is the secret of the proxmox api token `pve-auditor@pam!homepage`

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

<!-- the sidecar moved to docker/config-from-git.md. the empty span keeps
its old anchor working -->

<span id="the-sidecar"></span>the sidecar and gatus's `sparse-checkout`, `ssh_config` and `known_hosts` are on [config from git](../docker/config-from-git.md).

## a fork for the proxmox token

the proxmox quorum check needs an api token. upstream gatus only substitutes environment variables into its config, and a token in an environment variable is readable by anything that can read the service. i run a small fork that also reads `PROXMOX_TOKEN_FILE`, a docker secret, and substitutes `${PROXMOX_TOKEN}` from it.

## what each check asserts

each check asserts something only a working service returns, beyond a 200 from its web server:

| check | asserts |
| --- | --- |
| oauth2-proxy | `/ping` returns the body `OK` |
| frigate cameras | each camera the check names reports `camera_fps > 0` in `/api/stats` |
| glances, every host | `/api/4/quicklook` returns collected memory, `mem > 0` |
| proxmox | an authenticated `cluster/status` says the cluster is quorate |

## checking a job by its result

some services have no port: they wake, do a job and sleep. gatus checks those by what the job produces.

| service | checked by |
| --- | --- |
| cloudflare ddns | a name that is a CNAME to the DDNS record answers over TLS, with a valid certificate only my proxy holds |
| acme.sh, BMC and synology | the certificate each device serves verifies for its hostname and has more than 21 days left |
| auto-label nodes | the node labels it maintains are present, read through the docker socket proxy |

## checking a database through the app that uses it

the databases are only on their own stack's network. gatus joins none of those networks and checks each database through its app:

| database | checked through |
| --- | --- |
| npm's mariadb | NPM's `/api/`, which queries it on every call |
| wordpress's mysql | `/wp-json/`, which reads the site's options table |
| open webui's redis | open webui's `/ready`, which pings redis |

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
