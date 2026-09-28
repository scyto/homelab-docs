---
title: "Tasks & Scripts"
---

# tasks and scripts

what truenas1 runs at boot and on a schedule. the scripts live on a pool, in
`/mnt/fast/scripts`, so they survive an OS update.

## at boot

System → Advanced → Init/Shutdown Scripts

| when | script | does |
| --- | --- | --- |
| PREINIT | one per [system extension](sysexts.md), `/mnt/fast/.config/<name>/<name>-preinit.sh` | loads the extension before the apps start: hailo, coral, memryx, cli-tools, prometheus-exporters, the nvidia driver and the MIG setup |
| POSTINIT | `register-dns.sh` | registers the box's IPv4 and IPv6 addresses in DNS with `nsupdate` |

## cron jobs

System → Advanced → Cron Jobs, all as root

| when | runs | does |
| --- | --- | --- |
| daily 00:00 | `register-dns.sh` | the boot script again, to catch an address change |
| daily 04:00 | `configs-backup.sh` | backs up the newest snapshot of `fast/configs` to PBS, one archive per dataset, with a token that can only add backups. the 05:00 job then takes it to azure, encrypted |
| daily 05:00 | `pbs-cloud-backup.sh` | snapshots the PBS datastore and copies it to azure, encrypted with rclone crypt, using the cloud credential and the encryption password and salt stored on a cloud sync task in truenas, see [backups](../backups/index.md) |
| daily 21:00 | `portainer-s3-retention.sh` | keeps 14 nights of portainer's backups in the S3 bucket, and always the newest 14. portainer and versity gateway can't expire them, so it deletes the files, see [portainer to S3](../backups/portainer-s3.md) |
| daily 23:55 | `rsync` of `/mnt/.ix-apps/app_configs` | copies the catalogue apps' settings into `fast/configs/ix-app-configs`, root only, where the hourly snapshots and the replica on the rust pool pick them up. no snapshot or replication task can use a dataset under `ix-apps` |
| sunday 00:00 | `midclt call disk.smart_test` | a short SMART test on every disk. this version has no SMART test task, so cron runs it |
| sunday 04:30 | `docker image prune -a -f --filter until=168h` | truenas never removes an app's old image after an update, 225 GB had built up. keeping 7 days leaves the previous version to roll back to |

## snapshots

Data Protection → Periodic Snapshot Tasks

| dataset | when | kept |
| --- | --- | --- |
| `fast/configs`, recursive | hourly | 2 weeks |
| `fast/configs/versitygw` | daily | 30 days |
| `rust/S3` | daily, and sunday | 30 days, and 12 weeks |
| `rust/cloud-backups`, recursive | daily 05:00 | 2 weeks |

`fast/configs` holds every app's config, so one recursive task covers them all,
see [storage and snapshots](storage.md).

## scrubs

both pools are checked every sunday at midnight. a scrub runs when the last one
is more than 35 days old.

## cloud sync

| task | direction | when |
| --- | --- | --- |
| OneDrive for Business into `rust/cloud-backups/one-drive-4-business` | pull, copy | daily |
