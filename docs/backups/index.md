---
title: "Backups"
---

# Backups

how everything gets off the cluster. this section is being written as i rework
it, so parts describe a plan and say so. the backup server itself, retention,
verification and users, is on the [PBS page](pbs-server.md).

## what goes where

| what | how | lands on | state |
| --- | --- | --- | --- |
| VMs | proxmox backup job, snapshot mode, every two hours | PBS on [TrueNAS](../truenas/index.md) | working, see [VM backups](vm-backups-pbs.md) |
| cephFS (all swarm stack data) | `proxmox-backup-client` from a proxmox node, hourly | PBS on TrueNAS | working, being redesigned, see [cephFS backups](cephfs.md) |
| databases on cephFS | dumps written before the snapshot | cephFS, then PBS | planned |
| raspberry pi (pi-zwave01) | `proxmox-backup-client` on the pi, hourly | PBS on TrueNAS | working, see [raspberry pi](pi-host-backup.md) |
| portainer configuration | portainer's own scheduled backup | S3 on TrueNAS | working, see [portainer](portainer-s3.md) |

## the gap VM backups leave

a VM backup is the VM's disks. the swarm's shared data reaches the VMs over
[virtioFS](../proxmox/cephfs-virtiofs-passthrough.md), which is not a disk, so
**none of the stack data is in the VM backups.** that is what the cephFS backup
is for. same goes for anything a guest mounts itself, an RBD image or an NFS
share.

## rules i am working to

- **backups live off the thing they protect.** PBS and S3 are on the NAS, not on
  ceph
- **it is not off-site yet.** PBS and S3 are on the same box. PBS 4.2 supports
  S3-compatible storage as a datastore backend, which is the likely route for an
  off-site copy
- **the credential that writes backups should not be able to delete them.**
  PBS's `DatastoreBackup` role can back up and restore its own backups but not
  prune them, and retention is a prune job on the PBS side. the cephFS token has
  only that role. the VM storage still logs in as PBS `root@pam`, so that one is
  still to do
- **consistent beats live.** a copy of a database's files taken while it writes
  may not start. dump it, or snapshot first
- **silence is not success.** a failed backup should tell me. the VM job mails on
  failure. the cephFS job has nothing yet
- **a backup nobody has restored is a hope.** restore tests are still to do
