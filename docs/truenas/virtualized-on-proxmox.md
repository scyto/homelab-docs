---
title: "Virtualized on Proxmox"
source_gist: https://gist.github.com/scyto/305224b5e651f6d3c318744bfde99974
---

# virtualized on proxmox

for about a year truenas1 was a VM. it ran on **pve-nas1**, a single Proxmox host
that was never a member of the [cluster](../proxmox/index.md), and every drive it
used reached it by PCIe passthrough. ZFS in the VM talked to real controllers and
real disks, with no virtual disk anywhere in the storage path.

pve-nas1 is an AMD Epyc 9155 (Turin) on an ASRock Rack GENOAD8UD-2T/X550. that
matters more than it sounds, because the bulk storage hangs off MCIO connectors,
and how those enumerate shapes a lot of what follows.

it runs on bare metal now. **this page is kept for information.** it is the
configuration as it was, and it is what i would start from if i virtualized it
again. devices came and went over that year, so read the tables as the shape of
the thing rather than a parts list.

## key principle

anything the VM uses must be bound to `vfio-pci` on the host **before any host
driver can claim it**, and anything the host uses must never appear in the vfio
list. there are two ways to get this wrong and they fail differently:

- **the host claims the device.** `nvme` or `ahci` grabs the drive at boot,
  passthrough fails, and the VM starts without it
- **the host enumerates the pool.** far worse, and the reason this page exists.
  proxmox runs ZFS itself, and it will enumerate any pool it can see on a
  passed-through disk unless that device ID is kept away from it. two kernels
  with an opinion about one pool is how you lose it, and nothing warns you first

people will tell you the second one cannot happen, because the device is assigned
to a VM and excluded from the host. i am here to tell you it can. early in the
boot cycle, long before anything to do with virtualization has started, ZFS is
perfectly capable of claiming those drives.

that is why this takes **four** mechanisms and not whichever one you read about
first:

| | what it does |
| --- | --- |
| `blacklist` | stops the host loading a driver it has no use for at all |
| `softdep` | for drivers the host does need, loads vfio-pci ahead of them |
| `ids=` | names the devices vfio-pci should claim |
| udev rules | pin awkward devices by address or ID, whatever else happens |

drop the `softdep` lines and the `ids=` line is only a race. winning that race is the entire
point: a device already bound to `vfio-pci` has no storage driver behind it, so
the host cannot read a pool it cannot see.

!!! danger "never leave a pool exported across a host reboot"

    never export a pool in the TrueNAS VM and then reboot the host without
    importing it again in the VM first. an exported pool is one that nothing
    claims, and that is precisely the state in which the host will take it.

## what was on the bus

everything pve-nas1 could see, in bus order, and who ended up owning it. the
split in the last column is the whole design: four devices for the host, the rest
for the VM.

| BDF | vendor:device | device | bound to |
| --- | --- | --- | --- |
| `01:00.0` | `1e60:2864` | Hailo-8 AI processor | `vfio-pci` |
| `02:00.0` | `2646:5024` | Kingston DC2000B NVMe | `vfio-pci` |
| `03:00.0` | `2646:5024` | Kingston DC2000B NVMe | `vfio-pci` |
| `21:00.0` | `10de:2bb1` | NVIDIA RTX PRO 6000 Blackwell | `vfio-pci` |
| `42:00.0` | `1022:7901` | AMD FCH SATA (AHCI), MCIO connector A | `vfio-pci` |
| `42:00.1` | `1022:7901` | AMD FCH SATA (AHCI), MCIO connector B | `vfio-pci` |
| `83:00.0` | `1cc1:8201` | ADATA XPG SX8200 Pro NVMe | `vfio-pci` |
| `84:00.0` | `c0a9:5428` | Crucial T710 NVMe, 4 TB | `vfio-pci` |
| `a1:00.0` | `8086:2700` | Intel Optane SSD 900P | `vfio-pci` |
| `a3:00.0` | `8086:2700` | Intel Optane SSD 900P | `vfio-pci` |
| `a5:00.0` | `8086:2700` | Intel Optane SSD 900P | `vfio-pci` |
| `a7:00.0` | `8086:2700` | Intel Optane SSD 900P | `vfio-pci` |
| `a9:00.0` | not recorded | Intel X550 ethernet | `ixgbe`, **host** |
| `a9:00.1` | not recorded | Intel X550 ethernet | `ixgbe`, **host** |
| `ab:00.0` | not recorded | ASPEED BMC graphics | `ast`, **host** |
| `c1:00.0` | `1344:51c0` | Micron 7400 PRO NVMe | `nvme`, **host** |
| `c2:00.0` | `1344:51c0` | Micron 7400 PRO NVMe | `nvme`, **host** |
| `c3:00.0` | `15b3:1015` | Mellanox ConnectX-4 Lx, port 0 | `mlx5_core`, **host** |
| `c3:00.1` | `15b3:1015` | Mellanox ConnectX-4 Lx, port 1 | `mlx5_core`, **host** |
| `e1:00.0` | `1bb1:5018` | Seagate E18 NVMe | `vfio-pci` |
| `e2:00.0` | `1bb1:5018` | Seagate E18 NVMe | `vfio-pci` |
| `e3:00.0` | `1bb1:5018` | Seagate E18 NVMe | `vfio-pci` |
| `e4:00.0` | `1bb1:5018` | Seagate E18 NVMe | `vfio-pci` |
| `e6:00.0` | `1022:7901` | AMD FCH SATA, phantom | `vfio-pci` |
| `e6:00.1` | `1022:7901` | AMD FCH SATA, phantom | `vfio-pci` |

- the four Optanes are the SLOG devices, the four Seagates and the disks behind
  the two MCIO connectors are the bulk storage
- `e6:00.0/.1` are phantom. the chiplet topology exposes them but the board has no
  MCIO wiring behind them, so they get bound along with the real pair and that is
  harmless
- **the vendor:device IDs are dependable. most of the addresses are not.** the two
  SATA controllers sit on the FCH at `42:00.0/.1` and the GPU stayed at `21:00.0`
  for the whole year, but anything on an NVMe carrier moved more than once. a
  carrier reorder put the Hailo on a completely different bus, and simply adding
  the second boot NVMe pushed the Mellanox from `c2` to `c3`
- so the addresses in this table are one snapshot and the IDs are not. that is why
  everything below binds by ID where it can, and by address only for the two
  controllers that never move

## 1. what stays on the host

four devices, on their normal drivers: the two Micron 7400 PROs that are the
host's own `rpool` boot mirror, the Mellanox that is its data NIC, the X550 that
is its management NIC, and the ASPEED BMC console.

their vendor:device IDs are **deliberately absent** from the vfio list in step 2:

- `1344:51c0`, the Micron 7400 PRO. putting this on vfio takes the host's boot
  pool away from it
- `15b3:1015`, the Mellanox. putting this on vfio takes the host off the network.
  that is the usual ConnectX-4 Lx ID rather than one i read off this card, so
  confirm it with `lspci -nn -s c3:` before trusting it

everything else on the bus goes to the VM.

## 2. the modprobe rules

one file, `/etc/modprobe.d/vfio-pci.conf`, doing three jobs. i keep them together
rather than scattered across `blacklist.conf` and friends, because when this goes
wrong you want to read it all in one place:

```conf
# 1. drivers the host never needs, keep them out entirely
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset
blacklist hailo_pci

# 2. drivers the host does need, just not first
softdep nvme pre: vfio-pci
softdep ahci pre: vfio-pci
softdep hailo_pci pre: vfio-pci

# 3. what vfio-pci should claim
options vfio-pci ids=2646:5024,8086:2700,1cc1:8201,1bb1:5018,1e60:2864,1022:7901,10de:2bb1,10de:22e8
```

**blacklist where you can, softdep where you cannot.** that is the whole
distinction:

- the GPU and the Hailo have host drivers the host has no use for, so those get
  blacklisted outright
- `nvme` and `ahci` are different. the host boots off NVMe, so it needs `nvme`
  loaded. a blanket `blacklist nvme` would take the host's own boot pool out
  along with everything else
- for those two, `softdep nvme pre: vfio-pci` means "before you load `nvme`, load
  `vfio-pci` first". vfio-pci claims everything in `ids=` before the storage
  driver enumerates anything. it is **ordering, not exclusion**, and it is the
  line almost every guide leaves out
- `hailo_pci` gets both, because it costs nothing and that card caused enough
  trouble already (step 7)

**do not use the same NVMe device ID for the host's boot volume and anything you
pass through.** the `ids=` line cannot tell two identical drives apart, so if the
boot pool shares an ID with a passthrough drive you cannot have one without the
other. this is why the host boots off Micron 7400 PROs and nothing else on the
box is a Micron 7400 PRO.

what each ID catches:

| ID | catches |
| --- | --- |
| `2646:5024` | both Kingston DC2000B NVMe (`02:00.0`, `03:00.0`) |
| `8086:2700` | all four Intel Optane 900P (`a1`, `a3`, `a5`, `a7`) |
| `1cc1:8201` | ADATA SX8200 Pro (`83:00.0`) |
| `1bb1:5018` | all four Seagate E18 (`e1` to `e4`) |
| `1e60:2864` | Hailo-8 (`01:00.0`) |
| `1022:7901` | all four AMD FCH SATA controllers (`42:00.0/.1`, `e6:00.0/.1`) |
| `10de:2bb1` | NVIDIA RTX PRO 6000 Blackwell (`21:00.0`) |
| `10de:22e8` | Blackwell HDA audio. a no-op while the card is in compute mode, kept so flipping it back to display mode needs no edit |

!!! warning "one passed-through device is missing from that list"

    `84:00.0`, the Crucial T710, goes to the VM on `hostpci8`, but its ID
    `c0a9:5428` is **not** in the `ids=` line. that is how it is recorded in both
    places i have it from, so i have left it rather than quietly correcting the
    record, but it is a gap either way: nothing stops the host's `nvme` driver
    claiming that drive at boot. if you are copying this line, add `c0a9:5428`.

    the general check, before you trust any `ids=` line: every device in the
    `hostpci` map must be covered by an entry here.

- **bind by vendor:device, not by address.** one ID covers every identical drive,
  so adding another Optane needs no edit and a bus renumber breaks nothing

i worked the original list out with a script rather than by hand, because reading
`lspci` and missing one device is exactly the mistake that costs you a pool. it
takes the boot drives out of `zpool status` for `rpool` or `boot-pool`, excludes
those, and prints every remaining NVMe and SATA device as a `vendor:device` pair:
[scyto/virtio-fs-detection-and-exlusion](https://github.com/scyto/virtio-fs-detection-and-exlusion).

that repo also has an initramfs hook that binds by address at boot. **i abandoned
that approach as too fragile**: it carries a hard-coded list of BDFs, and BDFs
move on their own, so a hook written for one topology silently binds the wrong
thing after a card goes in. the modprobe and udev binding here replaced it. the
generator script is still worth keeping, it is the fastest way to get a correct
ID list on a rebuilt host.

## 3. pin the SATA controllers by address as well

`/etc/udev/rules.d/99-vfio-udev.rules`:

```udev
ACTION=="add", SUBSYSTEM=="pci", KERNELS=="0000:42:00.0", ATTR{driver_override}="vfio-pci"
ACTION=="add", SUBSYSTEM=="pci", KERNELS=="0000:42:00.0", RUN+="/bin/sh -c 'modprobe vfio-pci; echo 0000:42:00.0 > /sys/bus/pci/drivers/vfio-pci/bind'"
ACTION=="add", SUBSYSTEM=="pci", KERNELS=="0000:42:00.1", ATTR{driver_override}="vfio-pci"
ACTION=="add", SUBSYSTEM=="pci", KERNELS=="0000:42:00.1", RUN+="/bin/sh -c 'modprobe vfio-pci; echo 0000:42:00.1 > /sys/bus/pci/drivers/vfio-pci/bind'"
```

these are the two motherboard MCIO connectors, which is where the spinning disks
live. they are also the only devices whose address i am willing to hardcode: they
are on the FCH and they have never moved.

- a third layer on top of `1022:7901` and the `ahci` softdep in step 2. these two
  controllers carry the bulk pool, so i want them bound even if something
  interferes with the modprobe binding
- note the rules bind rather than unbind. if `ahci` has already claimed the
  controller by the time udev runs, the bind fails, which is why the load
  ordering in step 2 still matters
- `driver_override` sets the only driver the device will ever accept, and the
  `RUN+=` line binds it there and then rather than waiting

## 4. make sure vfio actually loads, then apply

everything above *configures* vfio-pci. none of it *loads* it, and a `softdep`
that points at a module the initramfs does not carry buys you nothing. so ask for
the modules explicitly.

`/etc/modules-load.d/vfio.conf`:

```conf
vfio
vfio_iommu_type1
vfio_pci
```

then rebuild the initramfs and reload the rules:

```
update-initramfs -u -k all
udevadm control --reload-rules
```

reboot for the modprobe changes to take effect.

- older guides, mine included, list a fourth module here, `vfio_virqfd`. it was
  folded into the vfio core in kernel 6.2 and no longer exists, so drop it
- `vfio-pci` has to be in the initramfs or the host's own drivers win the race at
  boot, which is the whole problem this page exists to solve

## 5. the VM itself

VM 100 as it stood. nothing exotic, and the only virtual disk was the one TrueNAS
booted from:

| | |
| --- | --- |
| machine | `q35` |
| BIOS | `ovmf`, with an EFI disk, `pre-enrolled-keys=1` |
| CPU | `32` cores, `1` socket, type `host`, `numa: 0` |
| memory | `131072`, ballooning down to `65536` |
| guest agent | on |
| boot order | `scsi0;ide2` |
| SCSI controller | `virtio-scsi-single` |
| boot disk (`scsi0`) | `local-zfs:vm-100-disk-1,cache=writeback,discard=on,iothread=1,size=64G,ssd=1` |
| network (`net0`) | `virtio`, on `vmbr0`, firewall on |
| TPM | `v2.0` |
| RNG | `source=/dev/urandom` |
| startup | `up=60` |

- `q35` because passthrough wants a PCIe machine, not the old i440fx PCI one
- CPU type `host`, not a model. ZFS wants the real instruction set
- the 64 GB boot disk lived on the host's `local-zfs`, so it was the one part of
  the NAS the host did own. everything holding data was passed through
- ballooning on a ZFS box is a matter of taste. the floor is 64 GiB so ARC never
  gets squeezed below something sensible

## 6. the hostpci map

one `hostpci` entry per passed-through device:

| slot | configuration |
| --- | --- |
| `hostpci0` | `0000:42:00.0,pcie=1,rombar=0` |
| `hostpci1` | `0000:42:00.1,pcie=1,rombar=0` |
| `hostpci2` | `0000:21:00.0,pcie=1,x-vga=0` |
| `hostpci3` | `0000:a1:00.0,pcie=1,rombar=0` |
| `hostpci4` | `0000:a3:00.0,pcie=1,rombar=0` |
| `hostpci5` | `0000:a5:00.0,pcie=1,rombar=0` |
| `hostpci6` | `0000:a7:00.0,pcie=1,rombar=0` |
| `hostpci7` | `0000:83:00.0,pcie=1,rombar=0` |
| `hostpci8` | `0000:84:00.0,pcie=1,rombar=0` |
| `hostpci9` | `0000:e1:00.0,pcie=1,rombar=0` |
| `hostpci10` | `0000:e2:00.0,pcie=1,rombar=0` |
| `hostpci11` | `0000:e3:00.0,pcie=1,rombar=0` |
| `hostpci12` | `0000:e4:00.0,pcie=1,rombar=0` |
| `hostpci13` | `0000:02:00.0,pcie=1,rombar=0` |
| `hostpci14` | `0000:03:00.0,pcie=1,rombar=0` |

- `rombar=0` everywhere. none of these need their option ROM exposed and leaving
  it on can stall the VM at boot
- `x-vga=0` on the GPU because it is a compute card, not the VM's console

two things do not fit the `hostpciN` form and live on an `args:` line in
`100.conf` instead:

```
args: -set device.hostpci0.x-msix-relocation=bar5 -set device.hostpci1.x-msix-relocation=bar5 -device pcie-root-port,id=pcie_hailo,addr=12.0,bus=pcie.0,chassis=20,hotplug=off -device vfio-pci,host=0000:01:00.0,bus=pcie_hailo,addr=0x0
```

- `x-msix-relocation=bar5` moves the MSI-X tables on the two SATA controllers.
  without it the VM will not start and you get this, which is what sent me down
  this road in the first place:

    ```
    vfio 0000:42:00.0: hardware reports invalid configuration, MSIX PBA outside of specified BAR
    ```

    this is not an ASRock quirk. it appears to be common to EPYC boards of this
    generation, so expect it on anything similar

- the Hailo-8 gets its own explicit `pcie-root-port` with `hotplug=off` rather
  than a `hostpciN` slot. that is a whole story of its own, see step 7

**add the two SATA controllers as discrete devices.** pass `42:00.0` and
`42:00.1` separately. do not select `42:00` and tick "All Functions", it does not
work on this board.

**the slot numbers above are one moment in time.** the bus renumbered more than
once over the year, as carriers were reordered and cards came and went, and the
`hostpciN` block had to be rewritten to match each time. read the pattern, not
the numbers.

**this block and the `host=` in `args:` are the only things a renumber breaks.**
they name addresses, so they need editing whenever the bus moves. the modprobe
rules and the Hailo udev rule name IDs, so they carry over untouched. that is the
argument for keeping as little as possible keyed on addresses.

!!! warning "a duplicate `hostpciN` key silently drops a device"

    i once ended up with two `hostpci14` lines after a renumber. nothing
    complains: the file parses, the VM starts, and one of the two devices simply
    is not there. if a drive goes missing after you edit the passthrough block,
    count the keys before you suspect the hardware.

    ```
    grep -o '^hostpci[0-9]*' /etc/pve/qemu-server/100.conf | sort | uniq -d
    ```

## 7. the Hailo-8, FLR and bus resets

the Hailo is the one device that does not sit in a `hostpciN` slot, and it took
three goes to get right. if you are passing one through, this is the section that
saves you the time.

**why it needs its own root port.** a function level reset makes the Hailo drop
off the bus and re-enumerate. the hotplug event that follows panics the host at
BIOS level, so Proxmox's ordinary `hostpci` path is unusable for it. instead it
gets the explicit `pcie-root-port` with `hotplug=off` from the `args:` line
above. when that is working the link event is logged and ignored rather than
acted on:

```
pciehp: Slot(20): Link Down/Up ignored
```

**choose the slot and chassis by hand.** my first version used `slot=10` and
`chassis=10`, and the VM started crashing as more devices went in: Proxmox
generates its own root port per `hostpciN` and those grew into chassis 5 to 16
and collided with mine. `addr=12.0, chassis=20` sits clear of them.

**then take FLR off the menu.** even with hotplug off, VM start took about two
and a half minutes, with this twice in the kernel log:

```
not ready 65535ms after FLR; giving up
```

each attempt burns 65 seconds before falling back to a secondary bus reset on the
parent port. the fix is to stop offering FLR at all:

```
cat /sys/bus/pci/devices/0000:01:00.0/reset_method     # flr bus cxl_bus
echo bus > /sys/bus/pci/devices/0000:01:00.0/reset_method
```

vfio then goes straight to the bus reset and the VM starts promptly. `cxl_bus` in
that list is irrelevant for this card.

**make it survive renumbering.** that write does not persist, and my first udev
rule keyed on the BDF, which broke the moment i reshuffled the NVMe carrier and
everything renumbered. the delay came straight back. key it on the vendor and
device ID instead, which survives a reshuffle.

`/etc/udev/rules.d/99-hailo-reset.rules`:

```udev
# Hailo-8 (1e60:2864): use bus reset instead of FLR
ACTION=="add|change", SUBSYSTEM=="pci", ATTR{vendor}=="0x1e60", ATTR{device}=="0x2864", ATTR{reset_method}="bus"
```

check it without rebooting:

```
udevadm trigger -s pci -c add
udevadm settle
cat /sys/bus/pci/devices/<BDF>/reset_method
```

- without `udevadm settle` the read races udev, and the first one still shows
  `flr bus cxl_bus`. read it twice before believing it
- this is the same lesson as the `ids=` line. key on what the device *is*, not on
  where it happens to sit today

## what virtualizing costs

mostly nothing, until you have to write to a device's own flash.

**card firmware cannot be flashed from inside the VM.** vfio passes MMIO through
but silently drops QSPI writes, so the flash tool reports success and the version
never changes. i hit this on the MemryX MX3, and its installer now refuses to try
from a guest at all:

```
ERROR: this TrueNAS is a VM (kvm). MX3 firmware CANNOT be flashed from a
  passthrough guest — VFIO silently drops the QSPI writes.
```

the fix is to do it on the host:

1. shut the VM down
2. unbind the card from vfio on the host, with the address from `lspci -d 1fe9:`

    ```
    echo 0000:XX:00.0 > /sys/bus/pci/drivers/vfio-pci/unbind
    ```

3. run the vendor's flash tool on the host
4. **full power cycle**, not a reboot. the card only reads its flash at power-on

the same shape of problem applies to any card whose firmware updater writes to
onboard flash. check before you assume an in-guest update worked, because the
failure is silent.

## sources

- [pve-nas1 PCIe device inventory and passthrough configuration](https://gist.github.com/scyto/305224b5e651f6d3c318744bfde99974),
  my own reference snapshot, where the tables come from
- [Passthrough of MCIO based SATA controller not working](https://forum.proxmox.com/threads/passthrough-of-mcio-based-sata-controller-not-working-msix-pba-outside-of-specified-bar.161831/),
  the Proxmox forum thread where i worked out the MSI-X relocation and the load
  ordering
- [scyto/virtio-fs-detection-and-exlusion](https://github.com/scyto/virtio-fs-detection-and-exlusion),
  the ID generator script, and the initramfs approach i abandoned
