---
title: "Databases"
---

# databases

a copy of a database's files taken while it writes may not start. every
database here has a copy that is consistent or checked, or doesn't need one.

| database | lives on | how it's copied | restore |
| --- | --- | --- | --- |
| wordpress, MySQL 8.0 | cephFS | [a dump sidecar](#a-dump-sidecar-wordpress), hourly | load the dump |
| gatus, SQLite | cephFS | [gatus copies itself](#gatus-copies-itself), hourly | swap the copy in |
| portainer, BoltDB | cephFS | [a checked copy in every cephFS backup](#portainer-a-checked-copy-in-every-cephfs-backup), hourly | put the file back |
| adguard, bbolt | cephFS | [none needed](#adguard-none-needed) | delete a bad file |
| the apps on truenas1, SQLite | ZFS | [snapshots](#the-apps-on-truenas1-zfs-snapshots), hourly, replicated to the rust pool, and nightly to PBS and azure | copy the files back |
| zigbee2mqtt and zwave-js-ui | the pi | [the pi's backup](#zigbee2mqtt-and-zwave-js-ui-the-pis-backup), hourly, and zwave-js-ui's own backups | restore the files |
| home assistant, the domain controllers | their VMs | the [VM backups](vm-backups-pbs.md), every two hours, with the guest agent freezing the filesystems | restore the VM |

## a dump sidecar: wordpress

the stack has a third service, `db-dump`, that asks the database for a
consistent copy at start and at :50 every hour. ceph snapshots at :00 and the
[cephFS backup](cephfs.md) ships the snapshot at :15, so every backup holds a
whole dump next to the database's own files.

| stack | dump | options |
| --- | --- | --- |
| [wordpress](../apps/wordpress.md#the-hourly-dump) | `wordpress_dumps/wordpressdb.sql`, about 70 MB | `--single-transaction` reads the InnoDB tables at one point in time without locking them. `--source-data=2` records the binary log position |

[nginx proxy manager](../apps/retired/nginx-proxy-manager.md) had the same
sidecar until it was retired. its last dump is in the [cephFS backups](cephfs.md)
made before 2026-10-03.

- the sidecar runs the database's own image, so `mysqldump` matches the server
- it needs no docker socket, reads the password the database already has, and
  lives in git with the stack
- it writes to a temporary name and renames the file only when the dump is
  complete, so a snapshot sees a whole dump or the previous one
- the dumps are uncompressed, because PBS compresses and deduplicates them
- it has no healthcheck. on the swarm a failing one restarts the task, which
  can't fix a missing database, and the script retries every five minutes

to restore, load the dump into a database server with no copy of that
database. the dump creates the database itself:

```
mysql -u root -p < wordpressdb.sql
```

the database's raw files from the same backup usually start too, and are
faster. for wordpress, the binary logs replay changes after the dump, up to a
chosen minute, see [rewinding to a minute](../apps/wordpress.md#binary-logs-and-rewinding-to-a-minute).

## gatus copies itself

gatus keeps its check history in SQLite, in WAL mode. a sidecar can't copy it
safely: WAL needs every process that opens the database on the same host,
swarm can't keep a sidecar on gatus's node, and the image has no shell. so
[my fork](../monitoring/gatus.md#the-fork) writes a copy with `VACUUM INTO`, at
start and at :50 every hour, to `gatus_data/backup/gatus.db`.

to restore, scale gatus to 0, delete `gatus.db-wal` and `gatus.db-shm`, copy
`backup/gatus.db` over `gatus.db`, and scale gatus back to 1. a leftover `-wal`
would be replayed into the restored file.

## portainer: a checked copy in every cephFS backup

portainer's database is BoltDB. it has no dump tool, and nothing outside
portainer can open it while portainer runs, so there is no sidecar. there are
three copies:

- the database's file in the hourly [cephFS backup](cephfs.md#4-the-backup). a
  snapshot holds it at one instant, which BoltDB is built to survive, and each
  run checks it with `bbolt check` before backing it up. a copy that fails is
  still backed up, and the run reports a failure. all 18 snapshots on the
  cephFS on 2026-09-26 passed. this is the copy i restore from
- the nightly backup to S3 on truenas, encrypted with a password i keep outside
  portainer, 14 nights kept, see [portainer to S3](portainer-s3.md). it copies
  the database file while portainer writes it, and mine has come back corrupt
  twice
- a cold copy, taken with portainer stopped, before every upgrade, see
  [cold copies](portainer-s3.md#cold-copies-before-an-upgrade). it is only as
  new as the last upgrade

to restore from the cephFS backup, scale portainer to 0 and take
`portainer_data/portainer.db` from the newest backup. PBS's web UI can download
one file from a backup. check it with `bbolt check`, which the backup container
has, copy it over the old one with `cp -a`, and scale portainer back to 1.

to restore from S3 instead, start a fresh portainer with an empty data volume
and choose "Restore Portainer from backup" on its first screen, then "Retrieve
from S3". it asks for the bucket's keys, the file name, the backup password, and
the setup token from portainer's log. i haven't tested either restore yet.

## adguard: none needed

adguard keeps its query statistics and web logins in two bbolt files,
`stats.db` and `sessions.db`, in `adguard_work/data` and `adguard_work2/data`.
both are disposable, and the config is YAML. if a restored one won't open,
delete it and adguard starts a new one.

## the apps on truenas1: ZFS snapshots

these keep SQLite databases under `/mnt/fast/configs`: sonarr, radarr,
prowlarr, bazarr, profilarr, seerr, sabnzbd's history, jellyfin, frigate,
open webui and grafana. `fast/configs` has a recursive snapshot every hour,
kept for three days, and one every midnight, kept for two weeks, see
[storage and snapshots](../truenas/storage.md#3-snapshot-the-config).
a replication task copies each snapshot to `rust/replicas/fast-configs` on the
rust pool, read-only, and keeps the same retention there. that covers losing the
fast pool. every night at 04:00, the newest snapshot is also backed up to PBS,
one archive per dataset, and the 05:00 copy takes it to azure, encrypted. that
covers losing truenas1.

- a ZFS snapshot is atomic, so a database in one looks like it went through a
  power cut. SQLite recovers from that
- sonarr, radarr and prowlarr also make their own scheduled backups, under
  `Backups/scheduled` in their config folders
- prometheus's metrics, ollama's models and open webui's redis cache are in
  ixVolumes, which have no periodic snapshots. all three can be rebuilt
- the catalogue apps' settings, in `ix-apps/app_configs`, are copied into
  `fast/configs/ix-app-configs` every night, root only, because truenas won't
  let a snapshot or replication task use a dataset under `ix-apps`. they hold
  secrets, such as versity's root keys

to restore one, stop the app and delete its current `-wal`, `-shm` and
`-journal` files if it has any. then copy the database, and whichever of those
files the snapshot has beside it, from `.zfs/snapshot/<snapshot>/` in the app's
dataset, or in its replica under `/mnt/rust/replicas/fast-configs` if the fast
pool is gone. use `cp -a`, which keeps each file's owner and mode. SQLite recovers
from the copied `-wal` or `-journal`, and a leftover one from the live folder
would be replayed into the restored file. a file owned by the wrong user leaves
the app with a read-only database.

## zigbee2mqtt and zwave-js-ui: the pi's backup

the [pi's backup](pi-host-backup.md) copies `/docker-data` every hour while both
apps run.

- zigbee2mqtt keeps its devices in `database.db`, a JSON-lines file, and the
  coordinator's network in `coordinator_backup.json`. it writes `database.db` to
  a temporary file and renames it, so a copy always gets a whole file
- zwave-js-ui keeps JSON-lines stores that a copy can catch mid-write. it also
  makes backups under `store/backups`: the store every day, keeping
  seven, and the controller's NVM. restore from the newest store backup rather
  than the live files

## still to do

- watch-your-lan on syn02 keeps a database in `/volume1/docker/wyl/data`. i
  haven't checked what backs that up
- an alert when a dump or a copy stops being refreshed. the jobs log a failure
  and retry, but nothing reports it yet
- restoring each of these, except the pi's files, is still to test
