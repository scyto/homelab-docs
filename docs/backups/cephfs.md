---
title: "CephFS Backups"
---

# CephFS backups

all the swarm's stack data lives on one cephFS, passed to the docker VMs with
[virtioFS](../proxmox/cephfs-virtiofs-passthrough.md). VM backups do not include
it, so it gets its own backup to PBS.

ceph takes a snapshot of the cephFS every hour on the hour. a small container
on the proxmox cluster backs up the newest snapshot to [PBS](pbs-server.md) at
quarter past, and proxmox HA restarts the container on another node when its
node goes down, so the backup doesn't depend on any one node.

| what | where |
| --- | --- |
| snapshots | ceph's `snap_schedule`, fs `docker`, path `/`, hourly, keeping 24 hourly and 7 daily |
| backup | a systemd timer in the container, hourly at :15 |
| source | the host's `/mnt/pve/docker-cephFS`, bind mounted read-only at `/mnt/cephfs` |
| destination | datastore `mnt-pbs`, namespace `Files`, group `host/cephfs` |
| credential | the API token `cephFS@pbs!cephFS`, with `DatastoreBackup` only |

a run takes about 15 seconds. the first one had nothing to compare against, so
it read all 10 GiB and took two minutes.

## 1. the snapshots

on any node:

```
ceph mgr module enable snap_schedule
until ceph mgr module ls | grep -Eq '^snap_schedule +on'; do sleep 2; done
ceph fs snap-schedule add / 1h --fs docker
ceph fs snap-schedule retention add / 24h7d --fs docker
ceph fs snap-schedule status / --fs docker
```

- the ceph manager takes the snapshots, so no particular node has to be up
- enabling a module restarts the manager, and `snap-schedule` fails with `not
  enabled/loaded` until it has loaded the module. the `until` line waits
- `--fs docker` names the filesystem. i have three, and without it the module
  uses the first in the fs map, which isn't this one
- 31 snapshots at a time is under the module's limit of 50 per directory, and
  `mds_max_snaps_per_dir`'s default of 100
- the snapshots are a quick local undo too: copy a file back out of `.snap`.
  they are on the same cluster, so they are not the backup

ceph documents its snapshots as asynchronous, with buffered data flushed lazily.
that is fine for config files but not for a database, see
[databases](#databases).

## 2. the container

a privileged debian 13 container, on `vDisks` so that HA can start it on any
node:

```
pct create <ctid> ISOs-Templates:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst \
  --hostname cephfs-backup \
  --ostype debian \
  --unprivileged 0 \
  --features nesting=1 \
  --cores 2 \
  --memory 1024 \
  --swap 512 \
  --rootfs vDisks:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,ip6=auto \
  --mp0 /mnt/pve/docker-cephFS,mp=/mnt/cephfs,ro=1,shared=1 \
  --hookscript ISOs-Templates:snippets/check-donotdelete-hook.sh \
  --timezone America/Los_Angeles \
  --onboot 1
ha-manager add ct:<ctid> --state started
```

- privileged, because files on cephFS belong to lots of different uids. an
  unprivileged container shifts uids, so through a bind mount files owned by
  uids outside its mapping show up as `nobody`, and anything not
  world-readable is off limits
- privileged means root in the container is root on the host. it runs nothing
  but the backup, and that is still better contained than a cron job on the
  node itself
- `ro=1` stops the container changing the data it backs up
- `shared=1` tells proxmox the path exists on every node, which lets the
  container move
- `nesting=1` lets debian 13's systemd set up its own mounts and service
  namespaces. without it the container boots with its network down
- the template has to be the `amd64` build. `pveam available` lists an `arm64`
  one too, which won't start on these nodes
- the container has no ceph client and no key of its own. ceph's own network is
  the thunderbolt mesh, and a guest reaches that through `vmbr100`, whose subnet
  is different on each node, so a container that moves would lose its route
- a container doesn't live-migrate. HA stops it on one node and starts it on
  another

## 3. the start guard

a bind mount is set up when the container starts. if cephFS isn't mounted on
the host at that moment, the container gets the empty directory under the mount
point, and keeps it after cephFS mounts. the container has the docker VMs'
[hookscript](../proxmox/cephfs-start-guards.md#hookscript), so it refuses to
start instead.

the script checks again before each run. it stops if `.snap` is missing, if
the newest snapshot is more than two hours old or dated more than a minute in
the future, or if the snapshot has no `.donotdelete` marker.

## 4. the backup

`proxmox-backup-client` comes from Proxmox's client repository. the script, the
timer and its unit go in the container, and the token goes in
`/root/.pbs-cephfs-token`, mode 600:

--8<-- "blocks/pve/cephfs-backup/pbs-client.sources.md"

--8<-- "blocks/pve/cephfs-backup/cephfs-backup.sh.md"

--8<-- "blocks/pve/cephfs-backup/cephfs-backup.service.md"

--8<-- "blocks/pve/cephfs-backup/cephfs-backup.timer.md"

- `DatastoreBackup` can back up and restore the backups its token owns, but not
  prune or delete them, so a compromised container cannot wipe the history.
  retention is the [prune job](pbs-server.md#retention-one-prune-job-for-everything)
  on the PBS side
- `--change-detection-mode=metadata` compares file metadata with the previous
  backup instead of re-reading everything
- `--ns Files` keeps these apart from the VM backups in the same datastore
- `proxmox-backup-client` reads only the first line of `PBS_PASSWORD_FILE`, so
  the newline at the end of the file is fine

## checking a restore

a backup that ran is not a backup that restores. `verify-restore`, in the
container, restores one top-level directory from the newest backup into `/tmp`
and compares it with the snapshot that backup read: the contents, and the
owner, group and mode of every entry. i run it before relying on a change to
how the backup runs:

```
pct exec <ctid> -- /usr/local/sbin/verify-restore
pct exec <ctid> -- /usr/local/sbin/verify-restore <directory>
```

--8<-- "blocks/pve/cephfs-backup/verify-restore.sh.md"

## still to do

- an alert when it stops. the script reports each run to a
  [gatus](../monitoring/gatus.md) external endpoint, and gatus alerts when no
  report arrives within two hours. the endpoint and its token don't exist yet,
  so for now the script logs that and backs up anyway
- encryption on the client, which `proxmox-backup-client` can do. the backups
  hold portainer's database, which has credentials in it. the key has to be kept
  somewhere other than the cluster. lose it and the backups are unreadable
- an alert when a [database dump](#databases) goes stale. the dumps log a
  failure and retry, but nothing reports it yet

## databases

snapshots alone are not enough for databases. a database keeps its state in
several files and in memory, and a snapshot can catch those files mid-write. so
each database gets a small dump job, a sidecar in its own stack, which asks the
database for a consistent copy just before the snapshot. the backup then holds
a dump known to be consistent as well as the raw files.

| stack | database | dump |
| --- | --- | --- |
| [wordpress](../apps/wordpress.md#the-hourly-dump) | MySQL 8.0, InnoDB | runs: `db-dump`, hourly at :50, `--single-transaction`, with the binary log position recorded |
| [nginx proxy manager](../apps/nginx-proxy-manager.md) | MariaDB 10.11, Aria tables | runs: `db-dump`, hourly at :50, `--lock-tables`, because `--single-transaction` only covers InnoDB. the database is 0.5 MB, so the lock is brief |
| portainer | its own embedded database | no dump tool. snapshot, plus portainer's own [backup to S3](portainer-s3.md) |
| [gatus](../monitoring/gatus.md#the-fork) | SQLite in WAL mode, its check history | runs: gatus copies itself with `VACUUM INTO`, hourly at :50. a sidecar can't: WAL needs every reader on gatus's host, and swarm can't place one there |

- the dump job runs the database's own image, so its `mysqldump` matches the
  server
- it needs no docker socket, reads the password the database already has, and
  lives in git with the stack
- it writes to a temporary name and renames the file only when the dump is
  complete, so a snapshot sees a whole dump or the previous one
- the dumps are uncompressed, because PBS compresses and deduplicates them
- to restore, load the dump into an empty database. the raw files from the same
  backup are usually fine too, and faster
- gatus's copy is a whole database, not a dump. to restore it, scale gatus to 0,
  delete `gatus.db-wal` and `gatus.db-shm`, copy `backup/gatus.db` over
  `gatus.db`, and scale it back to 1. a leftover `-wal` would be replayed into
  the restored file
