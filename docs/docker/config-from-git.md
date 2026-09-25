---
title: "Config from Git"
---

# config from git

[gatus](../monitoring/gatus.md) and [homepage](../monitoring/homepage.md) read config files from my repo as well as their compose file. so that changing one consumer never touches another, every stack that reads config from git carries its own [git-sync](https://github.com/kubernetes/git-sync) sidecar. the sidecar keeps a checkout of the stack's config folder on the cephfs mount.

## the sidecar

this is gatus's sidecar. it polls the stack's [deploy branch](gitops-with-portainer.md#3-one-branch-per-stack-not-main), `deploy/swarm/gatus`, every 60 seconds over ssh. the deploy key is read-only and held as a docker secret, and github's host key is pinned:

```yaml title="gatus/compose.yml"
  git-sync:
    image: registry.k8s.io/git-sync/git-sync:v4.7.1
    user: "1000:1000"
    environment:
      - TZ=America/Los_Angeles
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
        printf '%s\n' "$$(cat /run/secrets/gitsync_ssh_key_v1)" > /dev/shm/key
        [ -s /dev/shm/key ] || { echo "git-sync: could not write the SSH key to /dev/shm" >&2; exit 1; }
        mkdir -p /tmp/.ssh && cp /ssh_config /tmp/.ssh/config || { echo "git-sync: could not install the ssh config" >&2; exit 1; }
        exec /git-sync
    volumes:
      - type: bind
        source: /usr/share/zoneinfo
        target: /usr/share/zoneinfo
        read_only: true
      - type: volume
        source: gitrepo_v2
        target: /git
        volume:
          nocopy: true
    configs:
      - source: gatus_known_hosts
        target: /known_hosts
      - source: gatus_ssh_config_v1
        target: /ssh_config
      - source: gatus_sparse_checkout_v1
        target: /sparse-checkout
    secrets:
      - gitsync_ssh_key_v1
    networks:
      discovery:
        aliases:
          - gatus-git-sync
    deploy:
      mode: replicated
      replicas: 1
```

--8<-- "blocks/swarm/gatus/sparse-checkout.md"

--8<-- "blocks/swarm/gatus/ssh_config.md"

--8<-- "blocks/swarm/gatus/known_hosts.md"

- only the config folder is downloaded. `blob:none` makes a partial clone: commits and trees up front, and file contents only for what's checked out. the sparse checkout limits that to `config/`. it takes about 200K on disk instead of the whole repo, and nothing else in the repo lands on the shared storage
- the patterns have to list every parent. git-sync turns on git's cone mode, which ignores a bare folder path. `/stacks/swarm/gatus/config/` on its own checks out the top level files and no config folder, and gatus starts with nothing to check and looks healthy. don't put comments in that file either
- ssh gets its own timeouts. git-sync's sync timeout kills `git` but then waits on a stuck `ssh` underneath it, so a stalled connection hangs the sidecar. with these, ssh gives up after 15 seconds and git-sync fails and restarts
- the key is rewritten into `/dev/shm`. an openssh key must end with a newline, and my secret store strips trailing whitespace, so the entrypoint puts it back. `/dev/shm` is memory, so the key never hits a disk. if the write fails, the container stops with the reason instead of starting without a key
- uid 1000 needs `GITSYNC_ADD_USER` and `nocopy`. ssh won't run for a uid with no passwd entry, and without `nocopy` docker seeds an empty volume with the image's `/git`, ownership included
- `:8080` reports its health. it answers 5xx until the first sync, and git-sync exits on any failed sync, so a sidecar that keeps failing never answers 200. gatus checks it by its alias on the overlay, `http://gatus-git-sync:8080/`

## in another stack

only the names change: `GITSYNC_REF` names the stack's deploy branch, `sparse-checkout` its folder, the three configs take its prefix, `gitrepo_v2` binds its own folder on cephfs, and the alias is `<stack>-git-sync`. homepage's sidecar service is called `config-sync`, and it adds [a copy script](../monitoring/homepage.md#config-in-git).

## checking it

gatus checks each sidecar's `:8080`. this shows the latest result for both:

```
curl -s 'http://192.168.1.45:8085/api/v1/endpoints/statuses?page=1&pageSize=1' | jq -r '.[] | select(.key | startswith("plumbing_config-sync")) | "\(.key) \(.results[0].success)"'
```

```text
plumbing_config-sync-gatus true
plumbing_config-sync-homepage true
```

`false` means that sidecar is down, or has not synced since it started.
