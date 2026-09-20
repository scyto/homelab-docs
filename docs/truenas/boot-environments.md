---
title: "Boot Environments"
---

# boot environments

a boot environment is a bootable clone of the OS, selectable at the loader. it
is the way back from an update or a change that breaks booting, and it costs
almost nothing to make.

the thing worth knowing up front: **a clone you make is not protected until you
say so**, and the moment TrueNAS is most likely to remove one is during an
update — exactly when you wanted it.

## check what you have

```
midclt call boot.environment.query | python3 -m json.tool | grep -E '"id"|"active"|"keep"'
```

or Boot in the UI. what matters per entry:

| field | means |
| --- | --- |
| `active` | running right now |
| `activated` | what the loader will boot next time |
| `keep` | protected from automatic deletion |
| `can_activate` | selectable at the loader |

**one environment is not enough.** if the only entry is the active one there is
nothing to fall back to. i managed this by tidying up old clones without
noticing i had removed every alternative, on a beta release.

## 1. clone the running system

there is no `create` method, only `clone` — a new environment is always a copy
of an existing one:

```
midclt call boot.environment.clone '{"id": "<existing>", "target": "<new name>"}'
```

a name with the version and the date reads well later, e.g.
`rollback-26.0.0-<date>`.

it returns immediately and reports about 64 KiB. that is a ZFS clone sharing
blocks with its source, not a 5 GB copy — which is why there is no reason to be
sparing with these.

## 2. protect it

a fresh clone comes back `"keep": false`, which allows TrueNAS to prune it
automatically:

```
midclt call boot.environment.keep '{"id": "<new name>", "value": true}'
```

confirm:

```
midclt call boot.environment.query | python3 -m json.tool | grep -E '"id"|"keep"'
```

skip this and you have something that looks like a rollback target and may not
be there when you reach for it.

## naming, because it will mislead you later

name them after what they are *for*, not what made them. mine was called
`claude-safe-clone-<version>` — which reads like a spare copy, but was in fact
the live, running, active system, and the only one on the box.

if you ever prune by name, that is exactly the entry you would delete first.

## make one before an update

the whole point:

```
midclt call boot.environment.clone '{"id": "<active>", "target": "pre-<version>-<date>"}'
midclt call boot.environment.keep  '{"id": "pre-<version>-<date>", "value": true}'
```

the boot pool is usually mostly empty — mine is 4.8 GB used of 888 GB — so
keeping several costs nothing. check it is healthy while you are there:

```
zpool status boot-pool
```
