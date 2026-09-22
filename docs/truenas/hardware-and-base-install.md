---
title: "Hardware & Base Install"
---

# hardware and base install

what the NAS is built from, and the parts of the base configuration the rest of
these pages assume. running TrueNAS 26.0 on bare metal.

it was a VM on a single proxmox host for about a year before this, with every
drive passed through over PCIe. that setup is kept for reference in
[virtualized on proxmox](virtualized-on-proxmox.md).

## hardware

| part | what |
| --- | --- |
| board | ASRock Rack GENOAD8UD-2T/X550 |
| cpu | AMD EPYC 9115, 16 cores / 32 threads |
| memory | 192 GB ECC |
| network | 25GbE Mellanox (ConnectX, fibre) in use; onboard dual 10GbE (X550) idle |
| gpu | NVIDIA RTX PRO 6000 Blackwell Workstation Edition |
| accelerators | Hailo-8, MemryX MX3, 2 × Coral Edge TPU |

single socket, and the accelerator count is the unusual part. three different
inference accelerators sit in this box because frigate can run a detector on
each of them at once, see [frigate](../apps/frigate.md).

they all need a driver the base OS does not ship, which is what
[sysexts](sysexts.md) are for.

```
lspci | grep -iE 'nvidia|hailo|memryx|coral'
```

## the gpu is partitioned

the RTX PRO 6000 is split with MIG into three instances rather than handed to
one consumer whole:

| instance | size |
| --- | --- |
| 0 | 2g.48gb |
| 1 | 1g.24gb |
| 2 | 1g.24gb |

- MIG gives each consumer a hard slice of memory and compute, so one app cannot
  starve another
- each instance has its own UUID, and that UUID is what an app is given — not
  "the GPU". frigate gets one 1g.24gb instance, ollama and open-webui use the
  others
- the partitioning survives reboots via a sysext, see
  [sysexts](sysexts.md#nvidia-and-mig)

```
nvidia-smi -L
```

## disks and pools

18 drives, three pools:

| pool | topology | size | holds |
| --- | --- | --- | --- |
| `boot-pool` | mirror, 2 × 960 GB NVMe | 888 GB | the OS and [boot environments](boot-environments.md) |
| `fast` | 2 × mirror, 4 × 4 TB NVMe | 7.25 TB | apps, app config, container storage |
| `rust` | raidz2, 6 × 24 TB HDD + SLOG + L2ARC | 131 TB | media, backups, S3 buckets |

the drives:

| drive | count | where |
| --- | --- | --- |
| Seagate IronWolf Pro 24 TB | 6 | `rust`, raidz2 |
| Seagate FireCuda 530 4 TB NVMe | 4 | `fast`, two mirrors |
| Intel Optane 905P 960 GB | 1 | `rust` SLOG |
| ADATA XPG SX8200 Pro 2 TB NVMe | 1 | `rust` L2ARC |
| Kingston DC2000B 960 GB NVMe | 2 | `boot-pool` mirror |
| Intel Optane 905P (960 GB, 2 × 1.5 TB), Micron 7400 Pro 3.84 TB | 4 | not in a pool |

- **two mirrors rather than one raidz** on `fast`: it holds app databases and
  container root filesystems, so IOPS matter more than usable capacity
- **raidz2 on `rust`**: 24 TB drives take a long time to resilver, and raidz2
  survives a second failure during that window
- **the SLOG is Optane**, for low latency sync writes. the L2ARC is an ordinary
  NVMe drive
- every dataset uses lz4 compression and the default 128K record size, none
  are encrypted
- both pools are scrubbed on a schedule, see [tasks and scripts](tasks-and-scripts.md)

the dataset layout and what is worth snapshotting is its own page, see
[storage](storage.md).

```
zpool status
zpool list -o name,size,alloc,free,cap,health
```

## networking

one 25GbE link carries everything:

| setting | value |
| --- | --- |
| interface | one 25GbE fibre port (`mlx5`), static IPv4 |
| MTU | 9000 |
| other ports | onboard dual 10GbE (`ixgbe`), down |

- **jumbo frames end to end or not at all.** MTU 9000 here matches the rest of
  the LAN. a path where one hop is 1500 gives you connections that open and
  then stall on the first large transfer, which is a miserable thing to debug
- no LAGG. one 25GbE link is well past what the pools can serve, and the
  onboard 10GbE ports stay down rather than add paths nothing needs
- the [pbs container](containers.md) gets its own MAC on this same interface
  rather than a NAT, so it appears on the LAN as its own host

## identity and access

- **joined to an Active Directory domain**, so SMB shares authenticate against
  it and domain accounts resolve as users on the box. domain users appear as
  `MYDOMAIN\user` with high uids, distinct from local accounts
- the join has the account cache and dynamic DNS updates on
- a script also registers the box's IPv4 and IPv6 addresses in DNS with
  `nsupdate`, at boot and nightly, see [tasks and scripts](tasks-and-scripts.md)
- **apps do not run as you.** every catalog app runs as uid/gid **568**
  (`apps`), which is why a host path you created as root gives permission
  denied until it is chowned — see
  [the app gotchas](index.md#permission-denied-inside-the-app-on-a-host-path)
- **containers are id-mapped and isolated**, so root inside the container is an
  unprivileged uid on the host, see [containers](containers.md)
- **certificates come from the TrueNAS certificate store**, issued by Let's
  Encrypt over a DNS challenge. apps pick one in their config and TrueNAS
  restarts them when it renews

use the full hostname the certificate was issued for. the short name fails
verification and clients like portainer refuse it.
