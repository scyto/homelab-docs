---
title: "Backups"
---

# backups

how everything gets off the cluster. this section is being written as i rework
it, so parts describe a plan and say so. the [PBS page](pbs-server.md) covers
the backup server itself: retention, verification and users.

## what goes where

| what | how | lands on | state |
| --- | --- | --- | --- |
| VMs | proxmox backup job, snapshot mode, every two hours | PBS on [TrueNAS](../truenas/index.md) | working, see [VM backups](vm-backups-pbs.md) |
| cephFS (all swarm stack data) | `proxmox-backup-client` from a proxmox node, hourly | PBS on TrueNAS | working, see [cephFS backups](cephfs.md) |
| databases | a copy that is consistent on its own, one way per database | beside the database, then its backup | working, except portainer's and truenas1's. watch-your-lan's on syn02 is unchecked. see [databases](databases.md) |
| raspberry pi (pi-zwave01) | `proxmox-backup-client` on the pi, hourly | PBS on TrueNAS | working, see [raspberry pi](pi-host-backup.md) |
| portainer configuration | portainer's own scheduled backup | S3 on TrueNAS | working, see [portainer](portainer-s3.md) |
| the PBS datastore, off-site | a cron job on the NAS snapshots it and copies it, daily | azure blob storage | working, see [tasks and scripts](../truenas/tasks-and-scripts.md#cron-jobs) |

## what VM backups miss

a VM backup is the VM's disks. the swarm's shared data reaches the VMs over
[virtioFS](../proxmox/cephfs-virtiofs-passthrough.md), which is not a disk, so
**none of the stack data is in the VM backups.** that is what the cephFS backup
is for. they also miss anything a guest mounts itself, such as an RBD image or
an NFS share.

## rules i am working to

- backups live off the thing they protect. PBS and S3 are on the NAS, not on
  ceph
- PBS goes off-site every day. a cron job on the NAS snapshots the datastore
  and copies it to azure, see [tasks and scripts](../truenas/tasks-and-scripts.md#cron-jobs).
  S3 has no off-site copy
- the credential that writes backups should not be able to delete them.
  PBS's `DatastoreBackup` role can back up and restore its own backups but not
  prune them, and retention is a prune job on the PBS side. the cephFS and pi
  tokens have only that role. the VM storage still logs in as PBS `root@pam`, so
  that one is still to do
- dump a database or snapshot it first. a copy of a database's files taken while
  it writes may not start, see [databases](databases.md)
- a failed backup should tell me. the VM job mails on failure. the cephFS and pi
  jobs have nothing yet
- each backup needs a restore test. the pi has one, see
  [raspberry pi](pi-host-backup.md#5-prove-it-restores). the VMs, cephFS and
  portainer are still to do
