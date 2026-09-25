---
title: "CephFS Backups"
---

# CephFS backups

all the swarm's stack data lives on one cephFS, passed to the docker VMs with
[virtioFS](../proxmox/cephfs-virtiofs-passthrough.md). VM backups do not include
it, so it gets its own backup to PBS.

i am replacing what runs today with the plan below, which i have not built yet.

## what runs today

an hourly cron script runs on one proxmox node. the node mounts the cephFS
already, so `proxmox-backup-client` can read it directly. this is the script's
shape, with the token read from a file:

```bash
#!/bin/bash
# /etc/cron.hourly/ceph-backup   (chmod 700, see below)
export PBS_REPOSITORY='cephFS@pbs!cephFS@pbs1.mydomain.com:mnt-pbs'
export PBS_PASSWORD_FILE=/root/.pbs-cephfs-token     # chmod 600

proxmox-backup-client backup cephfs.pxar:/mnt/pve/docker-cephFS \
  --ns Files --change-detection-mode=metadata
```

- the token is an API token with `DatastoreBackup` on the datastore and
  nothing else. that role can back up and restore the backups it owns, but not
  prune or delete them, so a compromised node cannot wipe the history. retention
  is a prune job on the PBS side
- `--change-detection-mode=metadata` compares file metadata with the previous
  snapshot instead of re-reading everything
- `--ns Files` keeps these apart from the VM backups in the same datastore
- keep the token out of the script. scripts in `cron.hourly` are usually
  `0755`, readable by every local user. `chmod 700` the script and read the token
  from a `600` file with `PBS_PASSWORD_FILE`
- `proxmox-backup-client` does not cross mount points unless told to
  (`--include-dev`). one cephFS directory is one mount, so that is fine here

it runs every hour, and after PBS prunes there are dailies, weeklies and
monthlies back to mid 2025, about 13 GB each. it has three problems:

1. it runs on one node. when that node is down, nothing backs up
2. it reads the live tree, so databases on cephFS get copied mid-write
3. nothing tells me when it fails

## the plan

### back up from a snapshot

ceph can take cephFS snapshots on a schedule itself, with the `snap_schedule`
manager module, so no node has to be up to do it. the backup then reads the
newest snapshot under `.snap`.

- keep retention under `mds_max_snaps_per_dir`, which defaults to 100
- the snapshots are a quick local undo too: copy a file back out of `.snap`. they
  are on the same cluster, so they are not the backup

ceph documents its snapshots as asynchronous, with buffered data flushed lazily.
that is fine for config files but not for a database, see below.

### an unprivileged LXC with a read-only key

the script on one node becomes a container that proxmox HA can restart on any
node. it mounts cephFS itself with `ceph-fuse` and a key that can only read:

```
ceph fs authorize docker client.pbs-backup / r
```

that gives `mds allow r`, `mon allow r` and `osd allow r` scoped to the one
filesystem. a compromised backup container cannot change the data or touch the
host.

it mounts cephFS itself rather than bind mounting the host's. files on cephFS
belong to lots of different uids, and an unprivileged container shifts uids, so
through a bind mount files owned by host uids outside its mapping show up as
`nobody` and anything not world-readable is off limits.

three things are untested and need proving before i build it:

1. `ceph-fuse` mounts inside an unprivileged container (needs the container's
   `fuse` feature)
2. container root can read files owned by any uid through it
3. a key with only `r` can read `.snap`

if any of those fail, the fallback is a timer on every node that backs up only if
PBS has no snapshot from the last 45 minutes or so. whichever node is up does it.

### other bits

- one token, and a new backup group. PBS only lets `DatastoreBackup` write to
  groups its own token owns, so every runner uses the same token
- encryption on the client, which `proxmox-backup-client` can do. the backups
  hold database dumps and portainer's database, which has credentials in it.
  the key has to be kept somewhere other than the cluster. lose it and the
  backups are unreadable
- an alert when it stops. the runner pushes to a [gatus](../monitoring/gatus.md)
  external endpoint on success, and gatus alerts when no push arrives within the
  endpoint's heartbeat interval

## databases

snapshots alone are not enough for databases. each gets a small dump job in its
own stack, which writes to cephFS just before the snapshot, so the backup holds
a dump known to be consistent as well as the raw files.

| stack | database | dump |
| --- | --- | --- |
| wordpress | MySQL 8.0, InnoDB | `mysqldump --single-transaction` |
| nginx proxy manager | MariaDB with Aria tables | needs table locks, `--single-transaction` only covers InnoDB. small, so the lock is brief |
| portainer | its own embedded database | no dump tool. snapshot, plus portainer's own [backup to S3](portainer-s3.md) |
| gatus | SQLite, its check history | `sqlite3 .backup` from another container, since gatus's image has no shell. whether SQLite's locking holds over virtioFS and cephFS is still to test |

a dump job in the stack needs no docker socket, gets its password the same way
the app does, and lives in git with the stack.
