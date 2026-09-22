---
title: "Tasks & Scripts"
---

# tasks and scripts

what truenas1 runs at boot and on a schedule. scripts live in `/mnt/fast/scripts`, on a pool, so they survive an OS update.

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
| daily 05:00 | `pbs-cloud-backup.sh` | snapshots the PBS datastore and copies it to azure, using the cloud credential stored in truenas, see [backups](../backups/index.md) |
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

`fast/configs` holds every app's config, so one recursive task covers them all, see [storage and snapshots](storage.md).

## scrubs

both pools, checked every sunday at midnight. a scrub runs when the last one is more than 35 days old.

## cloud sync

| task | direction | when |
| --- | --- | --- |
| OneDrive for Business into `rust/cloud-backups/one-drive-4-business` | pull, copy | daily |
