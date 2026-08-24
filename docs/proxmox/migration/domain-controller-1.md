---
title: "Don't be like scyto"
source_gist: https://gist.github.com/scyto/ef59d3799c089338cfb32b83306f9396
---

# Don't be like scyto
## Don't do all the backup and restoring crap below
## Only reason vhdx import wouldn't work is becuause i mis-documented the command as `qm import..` when it is `qm disk import`
## I could easily have imported the vhdx all along.... learn my lesson padawan

original gist content

# Migrating Domain Controller 1 from Hyper-V to Proxmox by using Synology Backup
Why?  Well it turns out long lived VHDX's often error on import with qm and never import. 

## Introduction
So here we are about a month later (9/21/2023) and time to migrate DC1 to proxmox (i did DC2 first).
This has my FSMO roles.

So the image for this machine also failed to import with qm imports - there is something broken IMO with the support for VHDXs in qm, given searches reveal that this has been the case for years i don't expect to be fixed.  Yes it works with newly installed VM on server Hyperv 2022, but older VHDXs just seem to cause issues. YMMV,

tl;dr - backups from backup software are still essentials when using virtual disks - don't assume they can be mounted or converted or migrated to a different virtualization platform.

As such i chose to restore from synology backup using the bootable recovery media 

## synology steps (detail out of scope)
1. Install Active Bakcuop for Buisness backup agent on windows DC1 VM
2. Backup DC VM
3. Shutdown DC 1 VM
4. Create Synology Recovery media and uplaod the resulting ISO to your promox iso store

## Create VM (just unique items, assume you know how to do this)
1. remember to set boot from the recovery media
2. type windows (this is winpe)
3. default graphics
4. UEFI firmware with TPM
5. create disk virtio block as ID 1 and 32gb (we will be deleting this later
6. create disk IDE as IDE 1
7. set size to be a bit larger than the main partitions on your old VM - for me this  that was 71GB - this was smaller than the amount of files on the C:\ partition)
8. enable discard
9. caach = write through
10. NIC = virtio - but don't have it bound to any interface (i.e. not vmbrx)
11. after creation mount the virtio DVD as a SATA DVD

## Restore
1. boot VM
2. at load drivers load the viostor driver AND the NetKVM driver
3. proceed and enter the synoloy ip address, username and pasword
4. ignore any SSL error
5. chose the right backup - should be easy to know which one ;-)
6. choose to restore manually:
7. select  the backup version you want (latest)
8. choose just the c:\ not the reserved or EFI partitions,  (choose boot from the restore system volume)
9. say yes to all the warnings - hey its a VM who cares if it goes wrong ;-)
10. estimated time to restore ~50 minutes - actual ~11 mins (image is larger than dc2 because of gui install of server) 
11. eject media from VM
12. click turn off in the rercovery screen
13. make sure in the boot order options virtio is still enabled
14. cross fingers
15. restart VM
16. you should see a dew reboots etc and 'getting ready' and be able to login
17. login to the VM
18. in device manager whow hidden device
19. remove hyper-v network adpater (it should be grey)
20. in control panel change netwokr settings from DHCP to your original IP address settings
21. shutdown
22. now add the nic back to vmbr0
23. start the VM
24. check your DC is working prpoerly - be careful not to get worried by transient errors in dcdiag or repadmin
25. shutdown the VM 
26. detach the IDS disk (the disk will now appear as unused
27. double click it and add it back as virtio block, write through, discard = checked
28. chnage vm options to add virtio0 to the boot order 
29. start the VM
30. Machine should boot just fine
31. you are now good to go and can remove the virt1 temp disk any time you like (it is no longer needed)





<img width="646" alt="image" src="../../../assets/img/c4a0f4798725.png">

<img width="1669" alt="image" src="../../../assets/img/b78f7d753c44.png">
