---
title: "Stack Conventions"
---

# stack conventions

every stack in my repo follows these rules, swarm and [standalone](standalone/index.md) alike.

## one directory per stack

```
stacks/<env>/<stack>/compose.yml
```

- `<env>` is `swarm` or the host name. the deploy branch is `deploy/<env>/<stack>`, see [stacks in git](gitops-with-portainer.md)
- the directory name is the portainer stack name. service dns on the swarm is `<stack>_<service>`, so renaming a stack breaks anything that addresses it

## volumes are a named bind with `driver_opts`

```yaml
volumes:
  data:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/gatus_data"
      o: bind
```

- if the path is missing, the task refuses to start. a plain bind mount creates an empty directory, and the app starts against empty storage with no error. on a swarm that is a blank copy on whichever node the task landed on
- `docker volume rm` and `prune` remove the volume object, never the data at `device`
- the directory has to exist before the first deploy
- the path is always absolute. a relative path resolves inside portainer's clone of the repo, not on the host

on standalone hosts a plain bind is sometimes simpler. to make a missing source fail the same way, add `create_host_path: false`. this one is from syn02's dozzle agent:

```yaml
    volumes:
      - type: bind
        source: /usr/share/zoneinfo
        target: /usr/share/zoneinfo
        read_only: true
        bind:
          create_host_path: false
```

## pin images by digest

```yaml
    image: mysql:8.0@sha256:968e12b1fde035655c7a940db808b47372b70128293a38a3914e0b291c306e5e
```

a restart then never changes what runs. [renovate](image-updates-renovate.md#pin-images-by-digest) moves the tag and digest together by PR.

## swarm labels go under `deploy.labels`

```yaml
    deploy:
      labels:
        - homepage.group=Monitoring
```

labels on the container aren't visible to anything reading the swarm's services, so the [dashboard](../monitoring/homepage.md) never sees them. standalone hosts use plain `labels`.

## per-node services publish in host mode

```yaml
    ports:
      - target: 7007
        published: 7007
        mode: host
    deploy:
      mode: global
```

- published through the ingress mesh, the port load-balances across nodes, so a per-host tool answers from a random host
- address each node by its own IP. the keepalived VIP moves between nodes, so a check against it stays green while a node is down

## no healthchecks on swarm services

on the swarm a failing healthcheck gets the task killed and rescheduled. [gatus](../monitoring/gatus.md) checks health from outside instead. on a standalone host docker only reports health, so healthchecks are fine there, and mine say why they failed.

## every container runs in my time zone

```yaml
    environment:
      - TZ=America/Los_Angeles
```

images without tzdata ignore `TZ` with no error, so they get the host's zoneinfo read-only:

```yaml
    volumes:
      - type: bind
        source: /usr/share/zoneinfo
        target: /usr/share/zoneinfo
        read_only: true
```

check the app's own log timestamps after deploying. some images' `date` can't read zoneinfo even when the app can.

## secrets are never in the compose file

- passwords reach a container as a docker secret that the app reads from a file, never as the value of an environment variable. oauth2-proxy's cookie secret is the one exception
- secrets are listed by name only, under `x-secrets`, so a scan can tell a name from a value
- no labels holding credentials: labels are readable by anything that can read the service

how i manage them is [experimental](../secrets/index.md). docker secrets on their own are enough for most people.

## swarm configs are versioned by name

```yaml
configs:
  homepage_sync_config_v2:
    file: ./sync-config.sh
```

a swarm config can't be changed in place. a deploy that changes one fails with `only updates to Labels are allowed`. no service in the stack is updated, so the old content keeps running. bump the suffix when the file changes, which also restarts only the services that use it.
