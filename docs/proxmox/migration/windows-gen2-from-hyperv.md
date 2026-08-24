---
title: "How To migrate Gen2 Windows VM from Hyper-V"
source_gist: https://gist.github.com/scyto/e9cf5df1100edfdfb3a6104d6b288a1d
---

# How To migrate Gen2 Windows VM from Hyper-V

This assumes you have Windows Server 2022 Gen2 VM running on hyper-v that uses gen2  with UEFI and Secure Boot - it should work for win11 but i haven't tested that.  This has only tested with a vanilla windows server 2022 VM so far (three times to write guide).  I will comment this gist when i manage to move one of my domain controllers.

I suggest creating a fresh test windows VM and use this procedure on that test VM long before you try this on a production VM.
And repeat after me 'i will backup all VMs with snapshots AND will backup with backup application before i do this`... ok...

[this gist is part of this series](../index.md)

## VM preparation 
1. Dowload Virtio DVD and attach to running windows VM on Hyper-v
2. Log onto console of Windows VM to be migrated
3. Install VirtIO drivers (all drivers, this will also include spice tools)
4. Gracefully shutdown server
5. Export VM to CIFS location accessible by proxmox and mounted in proxmox

## Create Proxmox VM
1. Click create VM in top right corner
2. OS Tab
    - do not use any media
    - guest OS = windows  - 11/2022
3. System Tab
    - graphic card = default
    - machine = q35
    - BIOS = OVMF (UEFI)
    - EFI Storage = ceph pool rbd (e.g. vm-disks)
    - SCSI Controller = virtio SCSI single
    - QEMU agent = checked (note using shutdown in proxmox before OS is loaded will hand proxmox)
    - Add TPM = chcked
    - TPM storage = ceph pool rbd (e.g  vm-disks)
    - verion = v2.0
5. Disks Tab
    - delete the default IDE drive that gets createad
    - create a new disks with bus/device = VirtIO Block / 1
    - enable cache policy and discard aas you prefer
4.  CPU Tab - whatever you feel is right
5.  Memory Tab - whatever you feel is right
6.  Network Tab
    - bridge - vmbr0 or whatver custom bridges your have created
    - mode = VirtIO (paravirtualized)   
7. create VM but don't start it

## Import and attach disk to VM
1. in the shell navigate t the cifs mount point where you can see the vhdx exported earlier (or copy it to /temp)
2. execute `qm importdisk <VMID> <FILENAME>.vhdx <CEPH storage location>` for example if the VM in VM102 and the vhdx is called myserver.vhdx and the ceph pool is called vm-disks then the command would be:
```
qm disk import 102 myserver.vhdx vm-disks
```
The import will be slow initially, but if your VHDX was thin provisioned it will get faster when it only copies zeroes.
NOTE: while the disks might say it is 126 GB in the UI it will be thin prvisioned on the ceph volume and only take up the used amount of space inside the vhdx. Once the import has completed continue:

4. on `VM Name > hardware` double click `unused disk N` the number N may vary depending on situation
5. add it as ide 0, write though, ssd, discard and click `add`
6. in the gui `VM nane > options` chnage the boot order so IDE 0 is the number one device and check enable

<p align="center">
<img width="600" alt="image" src="../../../assets/img/446a851b37e9.png">
</p>

8. now go to the VM conole and click `start now`
9. logon to the VM once booted
10. now gracefully shutdown (do not use stop or reset)
11. on `VM Name hardware` select the IDE0 disk and click `detach`
12. now double click `unused disk 0` to re-add it
13. This time make it virtio block / 0 (also select discard and cache as you prefer and click `add`
14. in the gui `VM nane > options` chnage the boot order so virtio 0 and virtio 1 are both enabled and ensure the virtio 0 disk is the is the higest boot order device and click `ok`
<p align="center">
<img width="600" alt="image" src="../../../assets/img/c8f6481f920f.png">
</p>


You should be able to now start the VM and have it boot 100% fine.
On next shut down you can remove the small temporary virtio disk you created earlier.
