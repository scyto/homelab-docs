---
title: "System Extensions"
---

# system extensions

TrueNAS ships a fixed OS image. nothing i install with a package manager
survives an update, and `/usr` is read only. system extensions (sysexts) add
drivers and tools anyway, and they are what makes the
[accelerators](hardware-and-base-install.md#hardware) in this box usable.

a sysext is a squashfs image that systemd merges over `/usr` at boot. the base
image is untouched, so an OS update replaces the OS and leaves the extension
alone. it may leave it incompatible, though, see below.

## what is loaded here

```
systemd-sysext status
```

| extension | what it provides | from |
| --- | --- | --- |
| `nvidia` | GPU driver and runtime | TrueNAS |
| `nvidia-mig` | the MIG partitioning applied at boot | [community](https://github.com/truenas-community-sysexts/nvidia-mig-support) |
| `hailo` | Hailo-8 driver | [community](https://github.com/truenas-community-sysexts/hailo8-support) |
| `coral` | Coral Edge TPU (`gasket`/`apex`) driver | [community](https://github.com/truenas-community-sysexts/coral-pcie-support) |
| `memryx` | MX3 driver, firmware, and the `mxa-manager` daemon | [community](https://github.com/truenas-community-sysexts/memryx-mx3-support) |
| `cli-tools` | command line tools not in the base image | [community](https://github.com/truenas-community-sysexts/cli-tools) |
| `prometheus-exporters` | exporters for the metrics stack | [community](https://github.com/truenas-community-sysexts/prometheus-exporters) |

community means the
[truenas community sysexts](https://github.com/truenas-community-sysexts)
project on github.

without the driver extensions there is no `/dev/hailo0`, `/dev/apex_0` or
`/dev/memx0`, so nothing to pass to a container.

## where they live

```
/etc/extensions/        # symlinks, persistent
/run/extensions/        # staged at boot, tmpfs
/mnt/<pool>/.config/<name>/   # the actual .raw, on a pool
```

the images live on a pool, not on the boot device. `/run` is a tmpfs and `/etc`
is on the boot pool, so the copy that matters sits on `fast` and gets linked or
copied into place on every boot.

## how they get loaded on every boot

TrueNAS has init/shutdown scripts, and a PREINIT script runs before middleware
starts. each extension has one, set up in:

```
System → Advanced → Init/Shutdown Scripts
```

| when | script |
| --- | --- |
| PREINIT | `/mnt/<pool>/.config/<name>/<name>-preinit.sh` |

PREINIT runs before the apps service, so the device nodes exist before any
container that wants them starts. a driver that loads after frigate does
frigate no good.

each script is the same shape:

1. find its own directory by globbing `/mnt/*/.config/<name>`, so the pool name
   is not hardcoded and the script survives being moved
2. exit without an error if that directory is not there
3. link the `.raw` into `/run/extensions/`. the two nvidia scripts use
   `/etc/extensions/`, and the driver's image is copied first
4. `systemd-sysext refresh`
5. load the kernel module and start any daemon the hardware needs

they are written to be idempotent, so running one twice is harmless and the
script works on every boot, not only the first.

each community extension installs with the `get.sh` in its repo. it runs that
release's installer, which puts the `.raw` and its script on the pool and
registers the PREINIT entry:

```
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/nvidia-mig-support/main/get.sh | sudo bash -s -- --pool=fast
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/hailo8-support/main/get.sh | sudo bash -s -- --pool=fast
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/coral-pcie-support/main/get.sh | sudo bash -s -- --pool=fast
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/memryx-mx3-support/main/get.sh | sudo bash -s -- --pool=fast
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/cli-tools/main/get.sh | sudo bash -s -- --pool=fast
curl -fsSL https://raw.githubusercontent.com/truenas-community-sysexts/prometheus-exporters/main/get.sh | sudo bash -s -- --pool=fast --enable=<exporters>
```

- prometheus-exporters ships every exporter disabled, and `--enable` names the
  ones to run
- nvidia-mig takes its layout from `sudo configure-mig`, run after the install

## nvidia and MIG

two extensions do different jobs:

- `nvidia` is TrueNAS's own, symlinked from
  `/usr/share/truenas/sysext-extensions/nvidia.raw`
- `nvidia-mig` is from the community, and re-applies the
  [MIG partitioning](hardware-and-base-install.md#the-gpu-is-partitioned) at
  boot

MIG configuration does not persist by itself. without something re-applying it,
the card comes back whole after a reboot. every app that referenced a MIG UUID
then finds nothing, and fails in ways that do not obviously point at the GPU.

## memryx, in particular

the MX3 needs more than a kernel module. its extension also brings up
`mxa-manager`, a daemon exposing a socket directory:

```
/dev/memx0            # the device
/run/mxa_manager/     # the daemon's sockets
```

a container using the MX3 needs both the device node and a bind of the socket
directory, because the runtime talks to the daemon rather than driving the
device itself. it also needs to be privileged, which is why frigate does not
run as a catalog app, see [frigate](../apps/frigate.md).

this one is the
[community memryx sysext](https://github.com/truenas-community-sysexts/memryx-mx3-support).

## at upgrade time

sysexts are built against a kernel version. systemd checks compatibility and
refuses to merge one that does not match, so after a TrueNAS upgrade an
extension can stop loading. the first symptom is a missing device, not an error
about extensions.

so the upgrade routine is:

1. before upgrading, check whether a build exists for the version you are
   moving to
2. take a [boot environment](boot-environments.md) first
3. after the upgrade, confirm they merged and the devices are back:

```
systemd-sysext status
ls -l /dev/memx0 /dev/hailo0 /dev/apex_*
nvidia-smi -L
```
