---
title: "Proxmox Backup Server"
---

# proxmox backup server

PBS 4.2, running as a container on the [NAS](../truenas/index.md). one datastore,
which the [VM backups](vm-backups-pbs.md) and the [cephFS backups](cephfs.md)
both write to. this page is the PBS side.

## datastore

| name | path | garbage collection |
| --- | --- | --- |
| `mnt-pbs` | `/mnt/pbs` | daily 02:00 |

`/mnt/pbs` is a TrueNAS dataset handed to the container.

## namespaces

| namespace | written by |
| --- | --- |
| `VMs` | the proxmox [VM backup job](vm-backups-pbs.md), set on the proxmox storage |
| `Files` | the hourly [cephFS backup](cephfs.md), `--ns Files` |
| `CTs` | proxmox container backups. nothing writes it yet: the only PBS storage in proxmox is set to `VMs`, so a container job needs a second storage entry with `namespace CTs` |
| `Hosts` | file-level backups from other machines running `proxmox-backup-client`, each under its own token. today that is the [raspberry pi](pi-host-backup.md) |

`host/benchmark` in the root namespace is not a backup. `proxmox-backup-client
benchmark` uploads its test data to that group, so it appears the first time
someone runs a benchmark against the datastore.

## retention: one prune job for everything

```
proxmox-backup-manager prune-job list
```

| setting | value |
| --- | --- |
| store | `mnt-pbs` |
| namespace | none, so the root |
| max-depth | none, so every namespace below the root too |
| schedule | hourly |
| keep-last | 12 |
| keep-daily | 14 |
| keep-weekly | 8 |
| keep-monthly | 12 |
| keep-yearly | 5 |

one job at the root covers `VMs` and `Files` both. nothing on the proxmox side
prunes, the storage and the job are both `keep-all`, so this job is the only
thing that deletes backups.

what that keeps, given how often each thing backs up:

| rule | VMs, every 2 hours | cephFS, hourly |
| --- | --- | --- |
| last 12 | the last day | the last 12 hours |
| daily 14 | a backup a day for two weeks | same |
| weekly 8 | a backup a week for two months | same |
| monthly 12 | a backup a month for a year | same |
| yearly 5 | a backup a year for five years | same |

the rules apply in that order, and a backup already kept by one rule is not
counted again by the next.

## garbage collection

pruning only removes the index of a backup. the data lives in chunks shared
between backups, and garbage collection is what deletes chunks nothing references
any more, once they have gone unused for about a day. daily at 02:00.

```
proxmox-backup-manager garbage-collection status mnt-pbs
```

what the numbers looked like in September 2026:

| | |
| --- | --- |
| on disk | 1.02 TiB |
| backup data referenced | 30.1 TiB, in 972 indexes |
| deduplication | 29.6x |
| last run | 19 seconds, removed 1.2 GB |
| pending | 1.2 GB, unreferenced but still inside the one-day window |

the 29.6x is why keeping this much history is cheap. each backup of a VM shares
almost all its chunks with the one before.

## verification

```
proxmox-backup-manager verify-job list
```

| setting | value | meaning |
| --- | --- | --- |
| schedule | daily 04:00 | after pruning and garbage collection |
| ignore-verified | yes | skip backups that have already passed |
| outdated-after | 30 | re-verify anything last verified over 30 days ago |

so every backup is verified within a day of being taken, then again each month.
verification reads the chunks back and checks their checksums, which finds bad
disks before a restore does.

## users and permissions

```
proxmox-backup-manager user list
proxmox-backup-manager user list-tokens cephFS@pbs
proxmox-backup-manager acl list
```

| user or token | role on `/datastore/mnt-pbs` | used by |
| --- | --- | --- |
| `root@pam` | superuser | the proxmox [VM backup storage](vm-backups-pbs.md#1-the-pbs-storage) |
| `cephFS@pbs!cephFS` (token) | `DatastoreBackup` | the [cephFS backup](cephfs.md) |
| `cephFS@pbs` | `DatastoreBackup` | owns the token |
| `pi-zwave01@pbs!backup` (token) | `DatastoreBackup` on `Hosts` only | the [raspberry pi](pi-host-backup.md) |
| `pi-zwave01@pbs` | `DatastoreBackup` on `Hosts` only | owns the token |
| `backup@pbs` | `DatastoreBackup` | nothing i know of. not the pi, whose group is owned by its own token. check the owner column before removing it |

`DatastoreBackup` can create backups and restore the ones it owns. it cannot prune
or delete them.

the token has its own ACL entry as well as its user. PBS works out a token's
permissions from ACLs naming the token, and a token can never do more than its
user, so both need the role.

## certificate

```
proxmox-backup-manager cert info
```

a Let's Encrypt certificate for `pbs1.yourdomain.com`. it validates on an ordinary
debian CA store, full chain served. it also gets replaced every couple of months,
which matters for how clients are told to trust it.

**the proxmox PBS storage** trusts a certificate one of two ways, and they do not
mix (from `pve-apiclient`):

| storage has | proxmox checks | on renewal |
| --- | --- | --- |
| no fingerprint | the certificate chain **and** the hostname | nothing to do |
| a fingerprint | that fingerprint **only**, hostname checking off | the pin stops matching and every backup fails with `fingerprint ... not verified, abort!` until it is updated |

with a certificate from a public CA, leave the fingerprint off. a fingerprint is
for a self-signed certificate, which does not get replaced every couple of months.
the VM backup storage has none set.

**`proxmox-backup-client`**, used by the cephFS backup, has no `PBS_FINGERPRINT` set
and connects fine.
