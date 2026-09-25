---
title: "Boot Environments"
---

# boot environments

a boot environment is a bootable clone of the OS, selectable at the loader. it
is the way back from an update or a change that breaks booting, and it costs
almost nothing to make.

a new clone is not protected until you set `keep`, and TrueNAS may remove
unprotected clones during an update.

## check what you have

```
midclt call boot.environment.query | python3 -m json.tool | grep -E '"id"|"active"|"keep"'
```

or open Boot in the UI. the fields that matter for each entry:

| field | means |
| --- | --- |
| `active` | running right now |
| `activated` | what the loader will boot next time |
| `keep` | protected from automatic deletion |
| `can_activate` | selectable at the loader |

if the only entry is the active one, there is nothing to fall back to. tidying
up old clones can leave you there without noticing.

## 1. clone the running system

there is no `create` method, only `clone`. a new environment is always a copy
of an existing one:

```
midclt call boot.environment.clone '{"id": "<existing>", "target": "<new name>"}'
```

a name with the version and the date reads well later, e.g.
`rollback-26.0.0-<date>`.

it returns immediately and reports about 64 KiB. a ZFS clone shares blocks with
its source instead of copying 5 GB, so there is no reason to be sparing with
these.

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

## naming

name them after what they are for, not what made them. mine was called
`claude-safe-clone-<version>`, which reads like a spare copy. it was the active
system, and the only one on the box. if you ever prune by name, that is the
entry you would delete first.

## make one before an update

clone the active environment and keep the clone:

```
midclt call boot.environment.clone '{"id": "<active>", "target": "pre-<version>-<date>"}'
midclt call boot.environment.keep  '{"id": "pre-<version>-<date>", "value": true}'
```

the boot pool is usually mostly empty (mine is 4.8 GB used of 888 GB), so
keeping several costs nothing. check it is healthy while you are there:

```
zpool status boot-pool
```
