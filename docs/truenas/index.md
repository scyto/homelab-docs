---
title: "TrueNAS"
---

# TrueNAS

my NAS runs TrueNAS, outside the proxmox cluster. it holds the backups, and
because it does not depend on ceph, losing the cluster does not take the backups
with it.

it runs on bare metal. for about a year before that it was a VM on its own single
proxmox host, with every drive passed through to it over PCIe. that setup is kept
for information in [virtualized on proxmox](virtualized-on-proxmox.md).

what runs on it that the rest of these docs care about:

- proxmox backup server, in a TrueNAS container with its datastore on a dataset
  on the big pool. vm and cephfs backups land here, see
  [backups](../backups/index.md)
- S3 from [Versity Gateway](s3-versity-gateway.md), for things that know how to
  back themselves up to S3, like portainer
- portainer stacks from git: [the arr stack](../apps/arrstack.md),
  [frigate](../apps/frigate.md), [glances](../monitoring/glances.md) and the
  [dozzle agent](../monitoring/dozzle.md), see [truenas1](../docker/standalone/truenas1.md)
- catalog and custom apps, see [apps](apps.md)

PBS and S3 are on the same box. the PBS datastore is also copied to azure every
day, see [tasks and scripts](tasks-and-scripts.md#cron-jobs). S3 has no copy off
the box.

## pools

| pool | used for |
| --- | --- |
| `fast` | small pool: the apps dataset, and app config under `fast/configs/<app>` |
| `rust` | big pool: media, backups, S3 buckets |

## how it is put together

- [hardware and base install](hardware-and-base-install.md): the board, the
  accelerators, the pools and how the network and identity are set up
- [system extensions](sysexts.md): how drivers the base image does not ship
  get added, and survive a reboot
- [storage and snapshots](storage.md): dataset layout, and the rule that stopped
  a snapshot holding half a pool
- [apps](apps.md): what runs as a catalog app, where its storage goes, and the
  portainer agent
- [frigate](../apps/frigate.md): the NVR, four accelerators, and why it is not an app
- [containers](containers.md): the PBS system container
- [boot environments](boot-environments.md): making a rollback target, and
  protecting it so it survives the update you made it for

<!-- the app gotchas moved to the end of apps.md. the empty spans keep their
old anchors working -->

<span id="app-gotchas"></span><span id="an-app-starts-and-immediately-stops-and-the-ui-shows-no-logs"></span><span id="permission-denied-inside-the-app-on-a-host-path"></span><span id="host-paths-or-ixvolumes"></span><span id="certificates"></span>the app gotchas are at the end of [apps](apps.md#app-gotchas), symptom first.
