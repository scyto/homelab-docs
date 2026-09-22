---
title: "VM Backups to PBS"
---

# VM backups to PBS

one datacenter backup job sends the VMs to proxmox backup server, which runs as a
container on the [NAS](../truenas/index.md). this page is the proxmox side. the
PBS side, datastore, prune and verify jobs, gets its own page.

## 1. the PBS storage

Datacenter, Storage, Add, Proxmox Backup Server. what that leaves in
`/etc/pve/storage.cfg`:

```
pbs: pbs1-vms
        datastore mnt-pbs
        server pbs1.mydomain.com
        content backup
        namespace VMs
        prune-backups keep-all=1
        username root@pam
```

| setting | why |
| --- | --- |
| `namespace VMs` | VM backups get their own namespace. the [cephFS backup](cephfs.md) writes to `Files` in the same datastore |
| no `fingerprint` | PBS has a Let's Encrypt certificate, so proxmox checks the chain and the hostname and nothing needs changing when it renews. a pinned fingerprint would break at every renewal, see [certificate](pbs-server.md#certificate) |
| `prune-backups keep-all=1` | proxmox never prunes, retention belongs to PBS |
| `content backup` | backups only |

- the storage config is shared by the whole cluster, so this is one entry, not one
  per node
- the password lives separately, in `/etc/pve/priv/storage/pbs1-vms.pw`
- there is no encryption key configured (it would sit next to the password as
  `pbs1-vms.enc`), so these backups are not encrypted on the client

## 2. the backup job

Datacenter, Backup. what that leaves in `/etc/pve/jobs.cfg`:

```
vzdump: backup-582f465c-a553
        comment the pbs server manages retention (prune jobs)
        schedule */2:00
        enabled 1
        fleecing 0
        mailnotification failure
        mailto you@mydomain.com
        mode snapshot
        notes-template {{guestname}}
        pbs-change-detection-mode metadata
        prune-backups keep-all=1
        repeat-missed 1
        storage pbs1-vms
        vmid 111,103,104,106,113,112
```

| setting | what it does |
| --- | --- |
| `schedule */2:00` | every two hours, on the hour |
| `vmid` | the six VMs by ID, not "all". a new VM is not backed up until it is added here |
| `mode snapshot` | no downtime. with the guest agent running, the guest's filesystems are frozen for the moment the snapshot is taken |
| `fleecing 0` | off. fleecing is for backup targets slow enough to hold up the guest's own writes |
| `prune-backups keep-all=1` | the job never deletes a backup. the comment is there so nobody "fixes" it |
| `repeat-missed 1` | a run missed while the scheduler was not running happens as soon as it is back |
| `notes-template {{guestname}}` | PBS shows the VM's name, not just its ID |
| `mailnotification failure` | mail only when a run fails |
| `pbs-change-detection-mode metadata` | only affects container backups. this job has none, so it does nothing here |

each node runs the job for the VMs it hosts, all at the same time.

## 3. the VMs

| VMID | name | node | disks on | guest agent | also in the backup |
| --- | --- | --- | --- | --- | --- |
| 103 | winserver02 | pve2 | `vDisks` (ceph RBD) | on | EFI disk, TPM state |
| 104 | winserver01 | pve1 | `vDisks` (ceph RBD) | on | EFI disk, TPM state |
| 106 | homeassistant | pve3 | `vDisks` (ceph RBD) | on | EFI disk, TPM state |
| 111 | docker01 | pve1 | `local-lvm` | on | EFI disk, TPM state |
| 112 | docker02 | pve2 | `local-lvm` | on | EFI disk, TPM state |
| 113 | docker03 | pve3 | `local-lvm` | on | EFI disk, TPM state |

the docker VMs are on each node's own `local-lvm`, one per node, so for those
three the backup is the only copy of their disks that is not on that node. the
others are on ceph, which already keeps replicas across the nodes, and can move
between nodes.

`agent: 1` only tells proxmox to use the agent. the guest has to have it installed
and running (`qemu-guest-agent` on linux, the virtio guest tools on windows), or
there is nothing to freeze the filesystems with.

no disk is marked `backup=0`, so every disk is backed up.

## 4. what is not in these backups

- **virtioFS shares.** the docker VMs' `virtiofs0: docker-cephFS` is not a disk,
  so none of the swarm's stack data is here. see [cephFS backups](cephfs.md)
- anything a guest mounts for itself, an RBD image or an NFS share
- any VM not in the `vmid` list

## 5. checking a run

a failed run sends mail. to watch one from a shell, the per-VM lines go to the
journal under `pvedaemon`, on whichever node owns the VM:

```
journalctl -f SYSLOG_IDENTIFIER=pvedaemon | grep --line-buffered -E 'Backup of VM|Backup job|ERROR'
```

```
INFO: Starting Backup of VM 111 (qemu)
INFO: Finished Backup of VM 111 (00:01:15)
INFO: Backup job finished successfully
```
