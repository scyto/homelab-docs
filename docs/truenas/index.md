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

for data i care about i use a dataset i made, as a Host Path. an ixVolume lives
under the hidden apps dataset (`.ix-apps/app_mounts/<app>`), which is awkward to
point a snapshot task at, and deleting the app offers to remove its ixVolumes
along with it.

### certificates

pick the TrueNAS certificate in the app and use the **full hostname** it was
issued for. the short hostname fails TLS verification, and clients like
portainer will refuse it.

when the certificate changes, TrueNAS redeploys the apps using it, so an acme
renewal just restarts the app. nothing to do by hand.
