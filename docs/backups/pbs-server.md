---
title: "Proxmox Backup Server"
---

# proxmox backup server

PBS 4.2 runs in pbs1, a container on the [NAS](../truenas/index.md). it has one
datastore, which the [VM backups](vm-backups-pbs.md), the
[cephFS backups](cephfs.md) and the [raspberry pi](pi-host-backup.md) write to.

this page is PBS's own setup. the container is on the TrueNAS side:

- [building pbs1](../truenas/containers.md#building-pbs1): making the container
  and installing PBS in it. [setting it up](#setting-it-up), below, carries on
  from there
- [rebuilding pbs1](../truenas/containers.md#rebuilding-pbs1): replacing the
  container around the backups it already has

## setting it up

these steps carry on from
[building pbs1](../truenas/containers.md#building-pbs1), in its shell inside
the container. the sections after this one say what each part is set to, and
why.

1. create the datastore:

    ```
    proxmox-backup-manager datastore create mnt-pbs /mnt/pbs --gc-schedule 02:00
    ```

    - if the dataset already holds backups, add `--reuse-datastore true`.
      without it PBS refuses a directory that has files in it, with
      `datastore path not empty`
    - keep the name `mnt-pbs`. every client's repository names it

2. get the certificate. it comes from Let's Encrypt over a DNS challenge
   through Cloudflare, so pbs1 does not have to be reachable from the internet.
   first put the Cloudflare API token in a file, as one line,
   `CF_Token=<token>`:

    ```
    install -m 600 /dev/null /root/cf.env
    nano /root/cf.env
    ```

    then register, add the plugin and order:

    ```
    proxmox-backup-manager acme account register <account> <email>
    proxmox-backup-manager acme plugin add dns 1 --api cf --data /root/cf.env
    rm /root/cf.env
    proxmox-backup-manager node update --acme account=<account>
    proxmox-backup-manager node update --acmedomain0 pbs1.mydomain.com,plugin=1
    proxmox-backup-manager acme cert order
    ```

    - the token needs Cloudflare's DNS edit permission on the zone
    - `register` asks for a directory, and `0` is Let's Encrypt's production
      one. then it asks you to accept their terms
    - `cf` is acme.sh's Cloudflare plugin, and `1` is the id i gave the plugin
      in PBS. `plugin=1` makes the domain use it
    - PBS keeps its own copy of the token in
      `/etc/proxmox-backup/acme/plugins.cfg`, readable by root only, so the
      file can go
    - PBS renews the certificate itself. its daily update job orders a new one
      once the current one is within 30 days of expiring

3. add the users, tokens and ACLs, and the prune and verify jobs, as they are
   in [users and permissions](#users-and-permissions),
   [retention](#retention-one-prune-job-for-everything) and
   [verification](#verification), below.

    - they live in the container's `/etc/proxmox-backup`, not in the datastore,
      which is why [rebuilding pbs1](../truenas/containers.md#rebuilding-pbs1)
      saves that directory
    - garbage collection has no job of its own. step 1's `--gc-schedule` sets it

4. check it:

    ```
    proxmox-backup-manager datastore list
    proxmox-backup-manager cert info
    ```

    the datastore shows as `mnt-pbs` on `/mnt/pbs`, and the certificate's
    issuer is Let's Encrypt. clients connect by name, so `pbs1.mydomain.com`
    needs a DNS record pointing at pbs1. the web UI is then on
    `https://pbs1.mydomain.com:8007`.

    those checks don't cover logins, permissions or writes, so check both kinds
    of login before relying on it. on a proxmox node, the VM storage logs in as
    `root@pam` and should show `active`:

    ```
    pvesm status --storage pbs1-vms
    ```

    then run one token client's backup, such as the [cephFS backup](cephfs.md).

## datastore

| name | path | garbage collection |
| --- | --- | --- |
| `mnt-pbs` | `/mnt/pbs` | daily 02:00 |

`/mnt/pbs` is a TrueNAS dataset handed to the container, `rust/local-backups/pbs`,
on the hard-disk pool.

- `recordsize` is 1M, not the default 128K. a chunk is up to 4 MB, so it reads
  as about 4 records instead of 32, and the disks seek less. it applies to
  chunks written since 2026-09-26; older ones keep 128K until pruned

## namespaces

| namespace | written by |
| --- | --- |
| `VMs` | the proxmox [VM backup job](vm-backups-pbs.md), set on the proxmox storage |
| `Files` | app data: the hourly [cephFS backup](cephfs.md), and truenas1's [app configs](databases.md#the-apps-on-truenas1-zfs-snapshots) every night, `--ns Files` |
| `CTs` | proxmox container backups. nothing writes it yet: the only PBS storage in proxmox is set to `VMs`, so a container job needs a second storage entry with `namespace CTs` |
| `Hosts` | whole machines' files, from `proxmox-backup-client` on each under its own token. today that is the [raspberry pi](pi-host-backup.md) |

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

one job at the root covers `VMs`, `Files` and `Hosts`. nothing on the proxmox side
prunes: the storage and the job are both `keep-all`. this job is the only thing
that deletes backups.

this is what that keeps, given how often each thing backs up:

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
between backups, and garbage collection deletes the chunks nothing references any
more, once they have gone unused for about a day. it runs daily at 02:00.

```
proxmox-backup-manager garbage-collection status mnt-pbs
```

these were the numbers in September 2026:

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
| `truenas1@pbs!backup` (token) | `DatastoreBackup` on `Files` only | the nightly backup of truenas1's [app configs](databases.md#the-apps-on-truenas1-zfs-snapshots) |
| `truenas1@pbs` | `DatastoreBackup` on `Files` only | owns the token |
| `backup@pbs` | `DatastoreBackup` | nothing i know of. not the pi, whose group is owned by its own token. check the owner column before removing it |

`DatastoreBackup` can create backups and restore the ones it owns. it cannot prune
or delete them.

each token has its own ACL entry, as does its user. PBS works out a token's
permissions from ACLs naming the token, and a token can never do more than its
user, so both need the role.

## signing in with entra

users sign in to PBS with their entra ID accounts through an OpenID Connect
realm, set up the same way as proxmox's, see
[entra ID auth](../proxmox/extras/azure-ad-auth.md). PBS keeps its `pam` and
`pbs` password realms beside it.

!!! note "to be written"
    PBS's own realm settings, and its app registration in entra.

## certificate

```
proxmox-backup-manager cert info
```

PBS has a Let's Encrypt certificate for `pbs1.mydomain.com`. it validates on an
ordinary debian CA store, and PBS serves the full chain. it gets replaced every
couple of months, which matters for how clients are told to trust it.

**the proxmox PBS storage** trusts a certificate one of two ways, and they do not
mix (from `pve-apiclient`):

| storage has | proxmox checks | on renewal |
| --- | --- | --- |
| no fingerprint | the certificate chain **and** the hostname | nothing to do |
| a fingerprint | that fingerprint **only**, hostname checking off | the pin stops matching and every backup fails with `fingerprint ... not verified, abort!` until it is updated |

with a certificate from a public CA, leave the fingerprint off. a fingerprint is
for a self-signed certificate, which does not get replaced every couple of months.
the VM backup storage has none set.

**`proxmox-backup-client`** has no `PBS_FINGERPRINT` set for the cephFS and pi
backups, and connects fine.
