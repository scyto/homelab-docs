---
title: "Storage & Snapshots"
---

# storage and snapshots

how the datasets are laid out and which of them to snapshot. the pools
themselves (topology, disks, why raidz2 on one and mirrors on the other) are in
[hardware and base install](hardware-and-base-install.md#disks-and-pools).

a snapshot of a dataset whose app deletes its own data can hold far more than
the data: 3.34 TB against 71 MB of live data on frigate's cache, about half a
pool.

## dataset layout

| dataset | holds |
| --- | --- |
| `fast/configs/<app>` | config and databases. small, irreplaceable |
| `fast/<app>/media`, `fast/<app>/cache` | bulk data an app manages itself |
| `fast/.config/<name>` | [sysext](sysexts.md) images and their boot scripts |
| `fast/.truenas_containers/` | [container](containers.md) root filesystems |
| `fast/ix-apps`, mounted at `/mnt/.ix-apps` | TrueNAS's apps dataset: docker root, app configs, ixVolumes |
| `rust/local-backups`, `rust/cloud-backups` | PBS datastore, Time Machine, cloud sync |
| `rust/S3` | S3 buckets, see [Versity](s3-versity-gateway.md) |

every app's config sits under one parent, so a single recursive snapshot task
covers all of them and a new app is protected the day its dataset is created.

keep to one config tree. mine had both `fast/configs` and `fast/.configs`. they
differ by one leading dot and sort next to each other, and a snapshot task on
one covered none of the other. to merge them, move each child with
`zfs rename fast/.configs/<app> fast/configs/<app>`. check before writing any
snapshot task:

```
zfs list -o name | grep -i config
```

## the rule

**never snapshot a dataset whose application deletes its own data.**

an app with a retention policy (an NVR keeping 30 days, a cache, anything that
prunes) frees blocks as it goes. a snapshot pins those blocks, so the dataset
grows forever and the retention policy stops reclaiming anything.

what mine did while frigate was a catalog app:

| dataset | live data | held by snapshots |
| --- | --- | --- |
| frigate cache | 71 MB | **3.34 TB** |
| frigate media | 135 GB | 30 GB, climbing hourly |
| frigate config | 1.3 GB | nothing, there was no task |

the scratch was protected and the irreplaceable part was not.

i did not make those snapshots. TrueNAS snapshots the apps dataset before an
app upgrade and before a system update, so anything under `.ix-apps` is caught,
including bulk data left in an ixVolume. that is how a cache dataset ended up
holding terabytes.

for app config that automatic protection is useful, and it is all an ixVolume
can have. a periodic snapshot task cannot target an ixVolume, because
middleware does not expose those datasets. so an ixVolume can be recovered to
its last app upgrade, never to an hour ago. see
[apps](apps.md#storage-ixvolume-or-your-own-dataset) for when that is fine and
when it is not.

what to snapshot:

- **config:** snapshot it. it is small, changes rarely, and losing it is the
  thing you cannot fix
- **media and cache:** don't, or a day or two at most. the app's own retention
  is the policy and a snapshot fights it

## 1. find a snapshot eating a pool

`used` on a snapshot is the space unique to it, which is what you get back by
deleting it:

```
zfs list -t snapshot -o name,used -s used -r <pool> | tail -20
```

if a dataset's `used` is far larger than `du -sh` of its mountpoint, the
difference is snapshots.

## 2. delete one safely

check nothing depends on it, then dry run:

```
zfs get -H -o property,value clones,userrefs <snapshot>
zfs destroy -nv <snapshot>
```

`clones` of `-` and `userrefs` of `0` means nothing holds it. the dry run
prints what it would reclaim. then drop `-n`.

if no single snapshot looks big, they are sharing the blocks. `used` counts only
the space unique to one snapshot, so a 40 GB file held by seven of them shows as
~180 KB each, and deleting any one reclaims nothing. ask about the whole range
instead:

```
zfs destroy -nv <dataset>@<first>%<last>
```

that printed `would reclaim 39.6G` where every per-snapshot number looked
trivial. deleting the file alone does not help either: it moves out of `REFER`
and into `USEDSNAP`.

space returns asynchronously, so the pool figure lags:

```
zpool get -H -o property,value freeing,allocated,capacity <pool>
```

`freeing` back to `0` means it has finished.

## 3. snapshot the config

Data Protection → Periodic Snapshot Tasks → Add:

| field | value |
| --- | --- |
| Dataset | `fast/configs` |
| Recursive | yes |
| Schedule | hourly |
| Snapshot Lifetime | 2 weeks |

- recursive on the parent covers a new app the day you create its dataset, with
  nothing to remember
- hourly is cheap here because config barely changes. mine comes to 0 to 76 KB
  per dataset per snapshot, and the cost is metadata, not data
- this is only safe because these datasets do not delete their own data. the
  same schedule on media or cache is the mistake above

## 4. prove it runs

run it once by hand rather than waiting an hour:

```
midclt call pool.snapshottask.query | python3 -m json.tool | grep -E '"id"|"dataset"'
midclt call pool.snapshottask.run <id>
zfs list -t snapshot -r fast/configs | tail
```

## what this does not cover

snapshots are not backups: they are on the same pool as the data. the backups
kept on this box:

- PBS, in a [container](containers.md) here, takes proxmox and host backups, see
  [backups](../backups/index.md)
- S3, via [Versity](s3-versity-gateway.md), for things that back themselves up
- cloud sync to `rust/cloud-backups`

the PBS datastore is also copied to azure every day, see
[tasks and scripts](tasks-and-scripts.md#cron-jobs). S3 has no copy off the box.
