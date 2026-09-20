---
title: "TrueNAS"
---

# TrueNAS

my NAS runs TrueNAS and sits outside the proxmox cluster. for backups that is
the point of it: the box holding the backups does not depend on ceph, so losing
the cluster does not take the backups with it.

it runs on bare metal. for about a year before that it was a VM on its own single
proxmox host, with every drive passed through to it over PCIe. that setup is kept
for information in [virtualized on proxmox](virtualized-on-proxmox.md).

what runs on it that the rest of these docs care about:

- **proxmox backup server**, as a TrueNAS container, datastore on a dataset on
  the big pool. vm and cephfs backups land here, see [backups](../backups/index.md)
- **S3**, with [Versity Gateway](s3-versity-gateway.md), for things that know
  how to back themselves up to S3, like portainer

it is not off-site. PBS and S3 are on the same box, so they are a second copy,
not a disaster copy.

## pools

| pool | used for |
| --- | --- |
| `fast` | small pool: the apps dataset, and app config under `fast/configs/<app>` |
| `rust` | big pool: media, backups, S3 buckets |

## how it is put together

- [hardware and base install](hardware-and-base-install.md) — the board, the
  accelerators, the pools and how the network and identity are set up
- [system extensions](sysexts.md) — how drivers the base image does not ship
  get added, and survive a reboot
- [storage and snapshots](storage.md) — dataset layout, and the one rule that
  stopped a snapshot holding half a pool
- [apps](apps.md) — what runs as a catalog app, where its storage goes, and the
  portainer agent
- [frigate](frigate.md) — the NVR, four accelerators, and why it is not an app
- [containers](containers.md) — the PBS system container
- [boot environments](boot-environments.md) — making a rollback target, and
  protecting it so it survives the update you made it for

## app gotchas

stuff that took me a while, symptom first.

### an app starts and immediately stops, and the UI shows no logs

the UI has nothing to show for a container that exits straight away. docker
still has the logs. apps are compose projects named `ix-<app name>`:

```
docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -i <app>
docker logs --tail 50 ix-<app>-<service>-1
```

`/var/log/app_lifecycle.log` only gets written when compose itself fails. if
compose started the container and the process inside exited, there is nothing
in it, and a missing file is normal.

### permission denied inside the app, on a host path

apps run as the `apps` user, uid/gid **568**. give an app a Host Path and it does
**not** fix the ownership for you, the automatic permissions step only runs for
ixVolumes (checked in the app library source). a dataset created as root gives
`permission denied` the first time the app writes, which can look like an app
that keeps stopping, or a generic internal error.

```
ls -ldn /mnt/<pool>/<dataset>     # 0 0 means root owns it
chown 568:568 /mnt/<pool>/<dataset>
```

### host paths or ixVolumes

an ixVolume is the sensible default: it is chowned for you, and dying with the
app is a feature for config that means nothing without it. TrueNAS also
snapshots them before every app upgrade.

i use a dataset i made when i want either **point-in-time recovery** — a
periodic snapshot task cannot target an ixVolume at all — or the data on a
**different pool**, since an ixVolume always lands on the apps pool. see
[apps](apps.md#storage-ixvolume-or-your-own-dataset).

anything left under `.ix-apps` also gets caught by the automatic snapshots
TrueNAS takes before an update, which is its own problem: see
[storage and snapshots](storage.md).

### certificates

pick the TrueNAS certificate in the app and use the **full hostname** it was
issued for. the short hostname fails TLS verification, and clients like
portainer will refuse it.

when the certificate changes, TrueNAS redeploys the apps using it, so an acme
renewal just restarts the app. nothing to do by hand.

that convenience is app-only. a stack you run yourself binds the certificate
files and keeps serving the old one until you restart it, see
[frigate](frigate.md#certificates).
