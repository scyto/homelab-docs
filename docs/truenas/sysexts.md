---
title: "System Extensions"
---

# system extensions

TrueNAS ships a fixed OS image. nothing i install with a package manager
survives an update, and `/usr` is read only. **system extensions (sysexts) are
how drivers and tools get added anyway**, and they are what makes the
[accelerators](hardware-and-base-install.md#hardware) in this box usable.

a sysext is a squashfs image that systemd merges over `/usr` at boot. the base
image is untouched, so an OS update replaces the OS and leaves the extension
alone — though it may leave it *incompatible*, see below.

## what is loaded here

```
systemd-sysext status
```

| extension | what it provides | from |
| --- | --- | --- |
| `nvidia` | GPU driver and runtime | TrueNAS |
| `nvidia-mig` | the MIG partitioning applied at boot | mine |
| `hailo` | Hailo-8 driver | TrueNAS |
| `coral` | Coral Edge TPU (`gasket`/`apex`) driver | community |
| `memryx` | MX3 driver, firmware, and the `mxa-manager` daemon | community |
| `cli-tools` | command line tools not in the base image | community |
| `prometheus-exporters` | exporters for the metrics stack | community |

the driver ones exist because the hardware is useless without them: no
`/dev/hailo0`, `/dev/apex_0`, `/dev/memx0`, so nothing to pass to a container.

## where they live, and why that matters

```
/etc/extensions/        # symlinks, persistent
/run/extensions/        # staged at boot, tmpfs
/mnt/<pool>/.config/<name>/   # the actual .raw, on a pool
```

**the images live on a pool, not on the boot device.** `/run` is a tmpfs and
`/etc` is on the boot pool, so the copy that matters sits on `fast` and gets
linked or copied into place on every boot.

## how they get loaded on every boot

TrueNAS has **init/shutdown scripts**, and a PREINIT script runs before
middleware starts. one per extension:

```
System → Advanced → Init/Shutdown Scripts
```

| when | script |
| --- | --- |
| PREINIT | `/mnt/<pool>/.config/<name>/<name>-preinit.sh` |

PREINIT is the right hook because it runs **before the apps service**, so the
device nodes exist before any container that wants them starts. a driver that
loads after frigate does frigate no good.

each script is the same shape:

1. find its own directory by globbing `/mnt/*/.config/<name>`, so the pool name
   is not hardcoded and the script survives being moved
2. bail out quietly if that directory is not there
3. copy or link the `.raw` into `/run/extensions/`
4. `systemd-sysext refresh`
5. load the kernel module and start any daemon the hardware needs

they are written to be idempotent — running one twice is harmless — because a
boot script that only works once is a boot script that fails on the second
boot.

## nvidia and MIG

two extensions, doing different jobs:

- **`nvidia`** is TrueNAS's own, symlinked from
  `/usr/share/truenas/sysext-extensions/nvidia.raw`
- **`nvidia-mig`** is mine, and re-applies the
  [MIG partitioning](hardware-and-base-install.md#the-gpu-is-partitioned) at
  boot

MIG configuration does not persist by itself. without something re-applying it,
the card comes back whole after a reboot, every app that referenced a MIG UUID
finds nothing, and they fail in ways that do not obviously point at the GPU.

## memryx, in particular

the MX3 needs more than a kernel module. its extension also brings up
`mxa-manager`, a daemon exposing a socket directory:

```
/dev/memx0            # the device
/run/mxa_manager/     # the daemon's sockets
```

a container using the MX3 needs **both** — the device node and a bind of the
socket directory — because the runtime talks to the daemon rather than driving
the device itself. it also needs to be privileged, which is the reason frigate
does not run as a catalog app, see [frigate](frigate.md).

this one is built from the
[community sysext for TrueNAS](https://github.com/truenas-community-sysexts/memryx-mx3-support).

## the thing to remember at upgrade time

**sysexts are built against a kernel version.** systemd checks compatibility
and refuses to merge one that does not match, so after a TrueNAS upgrade an
extension can simply stop loading — and the first symptom is a missing device,
not an error about extensions.

so the upgrade routine is:

1. check whether a build exists for the version you are moving to, **before**
   upgrading
2. take a [boot environment](boot-environments.md) first
3. after the upgrade, confirm they merged and the devices are back:

```
systemd-sysext status
ls -l /dev/memx0 /dev/hailo0 /dev/apex_*
nvidia-smi -L
```

this is the cost of the approach, and it is the honest trade: hardware the base
image does not support, in exchange for a check you have to remember at every
upgrade.
