---
title: "Enable & Using vGPU Passthrough"
source_gist: https://gist.github.com/scyto/e4e3de35ee23fdb4ae5d5a3b85c16ed3
---

# Enable & Using vGPU Passthrough
This gist is almost entirely not unlike Derek Seaman's awesome blog:

[Proxmox VE 8: Windows 11 vGPU (VT-d) Passthrough with Intel Alder Lake](https://www.derekseaman.com/2023/06/proxmox-ve-8-windows-11-vgpu-vt-d-passthrough-with-intel-alder-lake.html)

As such please refer to that for pictures, here i will capture the command lines I used as i sequence the commands a little differently so it makes more logic to me. 

This gists assumes you are not running ZFS and are not passing any other PCIE devices (as both of these can require addtional steps - see Derek's blog for more info)

This gist assumes you are not running proxmox in UEFI Secure boot - if you are please refer entirely to dereks blog.

ALSO pleas refere to the comments section as folks have found workarounds and probably corrections (if the mistakes remain in my write up it is because i have't yet tested the corrections) 

Note:i made no changes to the BIOS  defaults on the Intel Nuc 13th Gen.  This just worked as-is. 

[this gist is part of this series](../../index.md)

## Preparation

### Install Build Requirements ###

```
apt update && apt install pve-headers-$(uname -r)
apt install git sysfsutils dkms build-* unzip -y
```
### Install Other Drivers / Tools
This allow you to run vainfo, intel_gpu_top  for testing and non-free versions of the encoding driver - without this you will not AFAIK be able to encoding with this GPU.  This was missed in EVERY guide i saw for this vGPU, so not sure, but i had terrible issues until i did this.

edits the sources list with `nano /etc/apt/sources.list`

add the following lines:
```
#non-free firmwares
deb http://deb.debian.org/debian bookworm non-free-firmware

#non-free drivers and components
deb http://deb.debian.org/debian bookworm non-free
```
and save the file

```
apt update && apt install intel-media-va-driver-non-free intel-gpu-tools vainfo
```

This next step copies a driver missing on proxmox installs and will remove the -2 error for this file in dmesg.
```
wget -r -nd -e robots=no -A '*.bin' --accept-regex '/plain/' https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/i915/adlp_dmc.bin

cp adlp_dmc.bin /lib/firmware/i915/
```

## Compile and Install the new driver

### Clone github project ###
```
cd ~
git clone https://github.com/strongtz/i915-sriov-dkms.git

```
### modify dkms.conf ###
```
cd i915-sriov-dkms
nano dkms.conf
```
change these two lines as follows:
```
PACKAGE_NAME="i915-sriov-dkms"
PACKAGE_VERSION="6.5"
```
save the file

### Compile and Install the Driver
```
cd ~
mv i915-sriov-dkms/ /usr/src/i915-sriov-dkms-6.5
dkms install --force -m i915-sriov-dkms -v 6.5
```
and use `dkms status` to verify the module is now installed

### Modify grub ###
edit the grub fle with `nano /etc/default/grub`

change this line in the file
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt i915.enable_guc=3 i915.max_vfs=7"
```
note: if you have already made modifications to this line in your grub file for other purposes you should also still keep those items

finally run

```
update-grub
update-initramfs -u

```

### Find PCIe Bus and update sysfs.conf ###

use `lspci | grep VGA` t find the bus number

you should see something like this:
```
root@pve2:~# lspci | grep VGA
00:02.0 VGA compatible controller: Intel Corporation Raptor Lake-P [Iris Xe Graphics] (rev 04)
```
take the number on the far left and add to the sysfs.conf as follows - note all the proceeding zeros on the bus path are needed
```
echo "devices/pci0000:00/0000:00:02.0/sriov_numvfs = 7" > /etc/sysfs.conf
```
**REBOOT**

## Testing On Host

### check devices ###

check devices with `dmesg | grep i915`

the last two lines should read as follows:
```
[    7.591662] [drm] Initialized i915 1.6.0 20201103 for 0000:00:02.7 on minor 7
[    7.591818] i915 0000:00:02.0: Enabled 7 VFs
```
if they don't then check all steps carefully

### Validate with VAInfo
validate with `vainfo` you should see no errors (note this needs the drivers and tool i said to install at the top)
and `vainfo --display drm --device /dev/dri/cardN` where N is a number from 0 to 7 - this will show you the acceleration endpoints for each VF

### Check you can monitor the VFs - if not you have issues
monitor any VF renderer in real time with `intel_gpu_top -d drm:/dev/dri/renderD128` there is one per VF - to see them all use `ls -l /dev/dri`

## Configure vGPU Pool in Proxmox

1. navigate to `Datacenter > Resource Mappings`
2. click `add` in PCI devices
3. name the pool something like `vGPU-Pool`
4. map all 7 VFs for pve 1 but NOT the root device i.e 0000:00:02.x **not** 0000:00:02
5. click `create`
6. on the created pool lcikc the plus button next to vGPU-Pool
7. select mapping on node = pve 2, ad all devices and click create
8.  repeat for pve3

The pool should now look like this:

![image](../../../assets/img/9b1e011ad857.png)


Note: machines with PCI pass through devices cannot be live migrated, they must be shutdown, migrated offline to the new node and then started.

# EVERYTIME THE KERNEL IS UPDATED IN PROXMOX YOU SHOULD DO THE FOLLOWING
```
update the kernel using proxox ui
dkms install -m i915-sriov-dkms -v 6.5 --force
reboot
```
