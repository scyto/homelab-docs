---
title: "swarm troubleshooting"
comments: true
---

# swarm troubleshooting

these took me a while to work out. each one starts with the symptom.

## a container can't reach a macvlan container on the same host

**symptom:** my uptime monitor kept saying dns on adguard `.5` was down, while
`.5` answered from every machine in the house, and `.6` on another node was fine.

**cause:** a container on a host cannot talk to a macvlan container running on
that same host. traffic leaves by the parent interface and never comes back.
containers on other hosts can reach it. macvlan is designed this way. the monitor
had landed on the node hosting `.5`.

**prove it**, from a container on the node in question:

```
docker run --rm alpine sh -c 'apk add -q bind-tools && dig +short @192.168.1.5 google.com'
```

on the node hosting `.5` it times out. anywhere else you get an answer.

**fix:** a macvlan shim called `mac0` on every host, see
[adguard](../apps/adguard.md#reaching-adguard-from-the-node-it-runs-on). it
routes only the two ipv4 resolver addresses, `.5` and `.6`.

## a published port keeps answering after you remove it

**symptom:** you remove a published port from a service. the spec no longer
lists it and `docker service inspect` is clean, but the port carries on answering
on every node in the swarm.

**cause:** removing the port updates the service spec but does not recreate the
running tasks. they keep their ingress network attachment, so the routing mesh
still sends them traffic.

**fix:** force the task to be recreated:

```
docker service update --force <service>
```

whenever a service behaves differently from its spec, the task is stale, and
`--force` recreates it. restarting the daemon does the same with more collateral.

i saw this on docker engine 28.0.4 and haven't filed it upstream, so i don't know
which other versions have it.

## deleting and recreating a stack fails on the network

**symptom:** you delete a stack and recreate it straight away, and it fails
saying the network already exists. the rollback then fails for the same reason,
which is how i took `dockerproxy` down.

**cause:** removing a stack tears down its `<name>_default` overlay network, and
that isn't instant. the recreate runs against a network that is still being
deleted.

**fix:** wait for the network to go, and retry if the first attempt fails:

```
docker network ls --filter name=<stack>_default
```

## portainer's stored copy isn't what's running

**symptom:** the compose stored in portainer differs from the running service.

**cause:** my portainer database had been restored from a backup at some point,
and several stacks in it did not match what was running. the differences were
small, but deploying the stored compose would have reverted changes.

**fix:** the **running container is the source of truth**. before converting
anything, compare the service's images, digests and every bind and device path
against what the compose says. two small scripts hitting the docker api were
enough.

## a restart upgraded everything

**symptom:** you recreate a stack expecting no change, and get new versions.

**cause:** no digest in the service spec means a restart re-pulls whatever the tag
points at right now. `mysql:8.0` today and `mysql:8.0` in six months are different
software.

recreating a stack feels like a reboot, but on an unpinned spec it's an upgrade of
everything in it.

**fix:** to make a recreate change nothing, pin the digest:

```yaml
    image: mysql:8.0@sha256:968e12b1fde035655c7a940db808b47372b70128293a38a3914e0b291c306e5e
```

then bump it deliberately as a commit you can revert.

## you can't edit a config or a secret

configs and secrets are immutable. neither an update nor a forced update changes
one. to change the contents, create a new one under a new name and repoint the
service. that is why names end up with `_v2` and `_v3` on them.

old versions stay until you delete them, so check now and again for ones nothing
references. a config named after its content instead of its version, like
`mqtt_config`, ends up wrong.

## a volume moved to cephFS is still on local disk

**symptom:** you change a stack's volume to a `driver_opts` bind onto cephFS and
redeploy, with no errors. but the container doesn't see what's on cephFS, and
what it writes doesn't show up there or on the other nodes.

**cause:** a volume with that name already existed on the node. docker reuses an
existing volume of the same name and driver and ignores the new `driver_opts`, so
the container carried on using `/var/lib/docker/volumes/<name>/_data` on that
node's own disk.

**prove it**, on the node running the task:

```
docker volume inspect <stack>_<vol> --format '{{json .Options}}'
findmnt /var/lib/docker/volumes/<stack>_<vol>/_data
```

good: the options show `device`, `o` and `type`, and findmnt shows
`docker-cephFS[/<dir>] virtiofs`. bad: options `null` or `{}`, findmnt prints
nothing.

**fix:**

1. remove the stack
2. on every node that has the volume (`docker volume ls -q --filter name=<stack>_<vol>`),
   look in its `_data` first. anything the service wrote since the change is
   there and nowhere else, so copy out what you need
3. `docker volume rm <stack>_<vol>` on each of those nodes
4. redeploy and check again

## docker won't start after a reboot or an upgrade

**symptom:** `docker.service` failed, and `systemctl status docker` shows the
`ExecStartPre` step exiting with status 1.

**cause:** the [data guard](../proxmox/cephfs-start-guards.md#docker-data-guard)
refused to start docker: the shared mount is missing, the sentinel file is
missing, or the mount has too few entries to be the real data.

**prove it:**

```
journalctl -u docker -n 20 --no-pager | grep data-guard
```

the `REFUSING TO START DOCKER` line says which check failed.

**fix:** fix the mount or the volume, then `sudo systemctl start docker`. don't
remove the guard to get docker back unless you know the data is where it should
be. the guard is there to stop docker starting when it isn't.
