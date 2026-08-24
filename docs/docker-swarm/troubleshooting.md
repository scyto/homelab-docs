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
