---
title: "swarm troubleshooting"
comments: true
---

# swarm troubleshooting

stuff that took me a while to work out, written down so future me doesn't do it
again. symptom first.

## a container can't reach a macvlan container on the same host

**symptom:** my uptime monitor kept saying dns on adguard `.5` was down, while
`.5` answered fine from every machine in the house. `.6` on another node was
fine too.

**cause:** a container on a host cannot talk to a macvlan container running on
that **same** host. traffic leaves via the parent interface and never comes back.
different hosts are fine. same host, no route. this is how macvlan works, not a
bug.

the monitor was telling the truth from where it happened to be running, it had
landed on the node hosting `.5`.

**prove it**, from a container on the node in question:

```
docker run --rm alpine sh -c 'apk add -q bind-tools && dig +short @192.168.1.5 google.com'
```

on the node hosting `.5` it times out, anywhere else you get an answer.

**fix:** a placement constraint keeping the monitor off the nodes running the
thing its monitoring.

if you monitor your own infrastructure from inside itself this will find you
eventually.

## a published port keeps answering after you remove it

**symptom:** removed a published port from a service, the spec no longer lists it,
`docker service inspect` is clean, and the port carries on answering on every
node in the swarm.

**cause:** not stale iptables rules, that was my first guess and it was wrong.
what leaked was the **task's network attachment**. the task still held its
attachment to the ingress network so the routing mesh still had somewhere to send
traffic, even though nothing in the service definition asked for it.

**fix:** force the task to be recreated

```
docker service update --force <service>
```

general move: if a service's observed behaviour disagrees with its spec, the task
is stale and `--force` recreates it. restarting the daemon does the same thing
with more collateral.

seen on docker engine 28.0.4, not filed upstream, so treat that as where i saw it
rather than where it exists.

## deleting and recreating a stack fails on the network

**symptom:** delete a stack, recreate it straight away, it fails saying the
network already exists. then the rollback fails for exactly the same reason,
which is how i took `dockerproxy` down.

**cause:** removing a stack tears down its `<name>_default` overlay network and
that isn't instant. you are recreating against a network that still exists while
being deleted.

**fix:** wait for it to actually go, and retry rather than treating the first
failure as terminal

```
docker network ls --filter name=<stack>_default
```

## portainer's stored copy isn't what's running

**symptom:** the compose stored in portainer differs from the running service.

**cause:** my portainer database had been restored from a backup at some point.
several stacks in it did not match what was running. not by much, but enough that
deploying the stored compose would have reverted changes.

**fix:** the **running container is the source of truth**. before converting
anything, compare what the service actually has against what the compose says,
images and digests, and every bind and device path. two small scripts hitting the
docker api were enough and they found real discrepancies.

## a restart upgraded everything

**symptom:** recreated a stack expecting a no-op, got new versions.

**cause:** no digest in the service spec means a restart re-pulls whatever the tag
points at right now. `mysql:8.0` today and `mysql:8.0` in six months are different
software.

matters most when you think you are doing something safe, recreating a stack
feels like a reboot but on an unpinned spec its an upgrade of everything in it.

**fix:** pin the digest if you want a recreate to change nothing

```yaml
    image: mysql:8.0@sha256:968e12b1fde035655c7a940db808b47372b70128293a38a3914e0b291c306e5e
```

then bump it deliberately as a commit you can revert.

## you can't edit a config or a secret

not with an update, not with a force. they are immutable. the only way to change
the contents is create a new one under a new name and repoint the service, which
is why names end up with `_v2` and `_v3` on them.

two consequences. old versions stick around until you delete them, so check now
and again which ones nothing references. and a config named after its content
rather than its version, like `mqtt_config`, ends up wrong.

## a volume moved to cephFS is still on local disk

**symptom:** changed a stack's volume to a `driver_opts` bind onto cephFS,
redeployed, no errors. but the container doesn't see what's on cephFS, and what
it writes doesn't show up there or on the other nodes.

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
   there and nowhere else, copy out what you need
3. `docker volume rm <stack>_<vol>` on each of those nodes
4. redeploy and check again

## docker won't start after a reboot or an upgrade

**symptom:** `docker.service` failed, and `systemctl status docker` shows the
`ExecStartPre` step exiting with status 1.

**cause:** the [data guard](../proxmox/cephfs-virtiofs-passthrough.md#docker-data-guard)
refused to start docker: the shared mount is missing, the sentinel file is
missing, or the mount has too few entries to be the real data.

**prove it:**

```
journalctl -u docker -n 20 --no-pager | grep data-guard
```

the `REFUSING TO START DOCKER` line says which check failed.

**fix:** fix the mount or the volume, then `sudo systemctl start docker`. don't
remove the guard to get docker back unless you know the data is where it should
be, that's the situation it's there to stop.
