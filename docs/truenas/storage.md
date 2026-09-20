---
title: "Storage & Snapshots"
---

# storage and snapshots

how the datasets are laid out and which of them are worth snapshotting. the
pools themselves — topology, disks, why raidz2 on one and mirrors on the other
— are in [hardware and base install](hardware-and-base-install.md#disks-and-pools).

the second half of this page matters more than it sounds. one snapshot on the
wrong dataset was holding **3.34 TB**, about half a pool.

## dataset layout

| dataset | holds |
| --- | --- |
| `fast/configs/<app>` | config and databases. small, irreplaceable |
| `fast/<app>/media`, `fast/<app>/cache` | bulk data an app manages itself |
| `fast/.config/<name>` | [sysext](sysexts.md) images and their boot scripts |
| `fast/.truenas_containers/` | [container](containers.md) root filesystems |
| `.ix-apps` | TrueNAS's apps dataset: docker root, app configs, ixVolumes |
| `rust/local-backups`, `rust/cloud-backups` | PBS datastore, Time Machine, cloud sync |
| `rust/S3` | S3 buckets, see [Versity](s3-versity-gateway.md) |

the shape that matters is **one parent holding every app's config**, so a
single recursive snapshot task covers all of them and a new app is protected
the day its dataset is created.

**don't end up with two config trees.** mine had `fast/configs` and
`fast/.configs` — one leading dot apart, sorting next to each other, and a
snapshot task on one covering none of the other. `zfs rename` merges them.
check before writing any snapshot task:

```
zfs list -o name | grep -i config
```

## the rule

**never snapshot a dataset whose application deletes its own data.**

an app with a retention policy — an NVR keeping 30 days, a cache, anything that
prunes — frees blocks on purpose. a snapshot pins exactly those blocks. the
dataset then grows forever and the retention policy silently stops reclaiming
anything.

what mine did:

| dataset | live data | held by snapshots |
| --- | --- | --- |
| frigate cache | 71 MB | **3.34 TB** |
| frigate media | 135 GB | 30 GB, climbing hourly |
| frigate config | 1.3 GB | nothing — there was no task |

exactly backwards: the scratch was protected and the irreplaceable part was not.

those snapshots were not mine. **TrueNAS snapshots the apps dataset before an
app upgrade and before a system update**, so anything under `.ix-apps` is
caught — including bulk data left in an ixVolume, which is how a cache dataset
ended up holding terabytes.

that automatic protection is genuinely useful for app config, and it is all an
ixVolume can have: **a periodic snapshot task cannot target one**, because
middleware does not expose those datasets. so the recovery granularity for an
ixVolume is "the last app upgrade", never "an hour ago". see
[apps](apps.md#storage-ixvolume-or-your-own-dataset) for when that is fine and
when it is not.

so:

- **config** — snapshot it. small, changes rarely, losing it is the thing you
  cannot fix
- **media and cache** — don't, or a day or two at most. the app's own retention
  is the policy and a snapshot fights it

## 1. find a snapshot eating a pool

`used` on a snapshot is the space unique to it — what you get back by deleting
it:

```
zfs list -t snapshot -o name,used -s used -r <pool> | tail -20
```

a dataset whose `used` is far larger than `du -sh` of its mountpoint says the
same thing from the other direction: the difference is snapshots.

## 2. delete one safely

check nothing depends on it, then dry run:

```
zfs get -H -o property,value clones,userrefs <snapshot>
zfs destroy -nv <snapshot>
```

`clones` of `-` and `userrefs` of `0` means nothing holds it. the dry run
prints what it would reclaim. then drop `-n`.

**if no single snapshot looks big, they are sharing the blocks.** `used` is the
space unique to one snapshot, so a 40 GB file held by seven of them shows as
~180 KB each, and deleting any one reclaims nothing. Ask about the whole range,
which is the only figure that tells the truth:

```
zfs destroy -nv <dataset>@<first>%<last>
```

that printed `would reclaim 39.6G` where every per-snapshot number looked
trivial. Deleting the file alone does nothing either: it moves out of `REFER`
and into `USEDSNAP`.

space returns asynchronously, so the pool figure lags:

```
zpool get -H -o property,value freeing,allocated,capacity <pool>
```

`freeing` back to `0` means it has finished.

## 3. snapshot the config

Data Protection → Periodic Snapshot Tasks → **Add**:

| field | value |
| --- | --- |
| Dataset | `fast/configs` |
| Recursive | yes |
| Schedule | hourly |
| Snapshot Lifetime | 2 weeks |

- recursive on the parent covers a new app the day you create its dataset, with
  nothing to remember
- hourly is cheap here because config barely changes. mine comes to 0–76 KB per
  dataset per snapshot; the cost is metadata, not data
- this is only safe because these datasets do not self-delete. the same
  schedule on media or cache is the mistake above

## 4. prove it runs

a task that has never fired is not a backup. run it once by hand rather than
waiting an hour:

```
midclt call pool.snapshottask.query | python3 -m json.tool | grep -E '"id"|"dataset"'
midclt call pool.snapshottask.run <id>
zfs list -t snapshot -r fast/configs | tail
```

## what this does not cover

snapshots are not backups — they are on the same pool as the data. off the box:

- **PBS**, in a [container](containers.md) here, taking proxmox and host
  backups, see [backups](../backups/index.md)
- **S3**, via [Versity](s3-versity-gateway.md), for things that back themselves
  up
- **cloud sync** to `rust/cloud-backups`

both PBS and S3 are on this same machine, so they are a second copy, not a
disaster copy.
