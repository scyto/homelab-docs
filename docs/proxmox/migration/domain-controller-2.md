---
title: "Don't be like scyto"
source_gist: https://gist.github.com/scyto/f8b0a1b06ae62f03db3182f8bd23abda
---

# Don't be like scyto
## Don't do all the restoring crap below
## Only reason vhdx import wouldn't work is becuause i mis-documented the command as `qm import..` when it is `qm disk import`
## I could easily have imported the vhdx all along.... learn my lesson padawan

original gist content

# Random Notes (stream of real-time conciousness) on Migrating Windows Server Core 2019 based AD domain controler

**tl;dr it worked - but due to an issue with the disk I had to use the synology bare metal restore into the VM and then use the disk shuffle approach i outlined in the parent gist to this one**

-------------

1. run a chkdsk - you want to be sure the drive is good
2. take a backup of the VM before you do anything esle 
3. DCdiag - run it, resolve any issues (you can ignore the 24 hour error message if thats the only one) othweise fix stuff before you move
4. my DC had one two werid errors, decided to upgrade to Server 2022 core before moving as it may explain some things.
5. tip if on server 2019 core use the command `DISM /online /Get-CurrentEdition` to check version - if it says standard only try and upgrade to 2022 standard core, not datacenter (or you will get really weird setup errors about product keys late and a roll back) and literally there is nothing on the internet to tell you what error means - took me 3 failed attempts to figure out i was using a datacenter key on a machine that needed a standard version to version upgrade..

... i am so glad I wrote this tip and then followed it - turns out some folders in syvol were not being replicated becayse they wre 808 days old!  that was challenging to fix... make sure you you run that dsdiag!!

6. to shrink or not to shrink, here is the thing, if you import a VHDX into proxmox it uses thin provisioning for the new RAW disk (even if it reports the internal size of the raw disk in the UI, it only is stored on ceph as a thin provisioned version) as such there is really no point in shriking or compacting a VHDX.... but what if you have OCD about this... well shrink the largest volume inside the VM with disk management (hope you used basic disks or you are SOL) and then use the hyper-v compact and optimize commands, this will help.  also defrag - the defrag command has lots of great options to trim the drive, reaarange slabs etc - consider using that SEE LATER:CONCLUSION DONT DO ANY OF THIS ITS WORSE THAN POINTLESS....

8. After installing the virtio CD (everything on it, reboot the DC to make sure it still works
9. now export the VHDX in hyper-v to a location you can copy from, then copy VHDX to a cluster node
10. now you can run import..`root@pve1~ qm import 103 winserver02-converted.vhdx vm-disks`

9. interestingly i hit this error on import (unles my test import), maybe don't run those defrag commands?
```
root@pve1:/mnt/pve/vhdximport/exported-vhds# qm import 103 winserver02-converted.vhdx vm-disks --format raw
winserver02-converted.vhdx:1: parser error : Start tag expected, '<' not found
vhdxfileM
^
```
So i thought about restoring from my synology backups directly into an empty proxmox VM. 
So i did an online agent based backup worked
Then i shutdown VM to do a VM based backup didn't - i was told i needed to expand the disk due to issues so i expandined the dynanmic disk from 167gb to 168gb (note the disks is about 40gb in real szie and the partition inside is about 69gb - i really think running defrag and compact was not a great idea....)

now vm backup on synology is working ... gottawait for that to finish....

ok I will try exporting the file once more and see if the same thing causing the synology issue was causing the qm import issue or no....

nope didn't fix

ok lets try to convert it to a diff format

qemu-img convert -O qcow2 winserver02.vhdlswinserver02.qcow2

ok converting to QCOW didn't change issue

nope same errors - nothing likes this disk excepy hyper-v and synology....



ok time to see  synoligy bare metal restore....


First create the synology recovery media.
Then the VM - make new HDD IDE - need to be same size as the parititons added together in the VM (not including empt unallocated space)
Make network virtuio
mount the recovery CD and the virtio CD
boot from recover CD
adn the NetKVM driver and and vstor driver when prompted (browse the virtio cd)
choose if you want to restore all partitions (i seemed to have two recovery parts and i never use those, so i decided to see what would happen if i restrored just the system and EFI partitions....

Well thats cool, and it only took 3 minutes to complete

<p align="center">
<img width="800" alt="image" src="../../../assets/img/0be11f8a2b1c.png">
</p>

Once it restore i treated the machine as if it had had the disk imported and did the first boot as IDE with a dummy virtio attached then shutdown unattateched disk and reattahced as block and booted.  All is ok.

and pus side, restoring 'bare metal' into the VM allowed me to shrink the disk from 169GB to 70GB which is nice.

One DC on promox, will let this run for a few days and then see where i am at.

The hardest part after the disk issues was how to set ipv6 on server core - [this article](https://develmonk.com/2022/11/23/windows-server-core-setting-a-new-ip-address-for-your-dc-including-ipv6-client-dns/) was super helpful.

So what did i learn:
1. make sure DCs are healthy before doing anything
2. backup the DCs multiple ways before doing anything
3. don't rely on the virtual disk format to be importable and that conversion to other formats won't fix a disk qm doesn't like
4. the synology bare metal restore was kinda awesome - i am still a little confused if it pulled from the physical server backups (aka the agent in the VM) or the direct hypervisor backups....  hmm looking at the task names it was the agent one it pulled from... either way - cool!
