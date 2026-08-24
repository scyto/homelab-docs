---
title: "Setup HA Windows VM"
source_gist: https://gist.github.com/scyto/054c153defe3acbbe3a61d6fe08704d4
---

# Setup HA Windows VM
this example uses windows server 2022.  Windows 11 will be basically the same

It is beyond this gist to be a deep tutorial.

[this gist is part of this series](index.md)

## Prep
1. Download your windows ISO of choice (i am using windows 2022 Data Center for this example.)
2. Download the lates virtio.iso too
3. go to `Datacenter > pve1 > expand child nodes in left pane > local (pve1)` (i don't know why i find this unintutive)
4. click `ISO Images`
5. click `upload` and path to your ISO and click `upload` - you will need to do this on every node you want to create VMs on (ISOs are not replicated by default - [but see this is you want to replicate across nodes](cephfs-and-storage.md))

## Create VM
1. on the node you uploaded the click the `create VM` in the upper right corner
2. on the General page you need to specify a `name` and the click `next`
3. on the OS page 
  - set the ISO to boot, select your storage and then select the iso image from the drop down
  - set guest OS to windows and the latest date
  - click next
4. For the system page it is imperative you pick the pool you created ealier for EFI and TPM storage as follows:
<p align="center">
<img width="600" alt="image" src="../../assets/img/c0090a770284.png">
</p>

5. Set the disk to virtio block storage for max perf
6. it is also important to select the ceph pool when creating disks for the VM as follows (note my personal preference to use write through for the cache policy - i don't care about loosing reads, i do care about loosing writes; the discard setting is outside the scope of this gist.
<p align="center">
<img width="600" alt="image" src="../../assets/img/a5b960065a8b.png">
</p>

**do not start the VM at this point.**

## Attach and configure Virtio Block Storage driver during OS install
1. navigate to `Datacenter > pve1 > vmnode > hardware`
2. click `add`
3. choose `cd / dvd drive`
4. set as `SATA2`
5. choose your storage and the virtio ISO Image and click ok.
6. now boot the VM and press key to boot from DVD
7. when it ask where you want to install OS it will ve blank - click `load driver`
8. click `browse`
9. navigate to the virtio CD drive (e.g D: or whatver letter it has)
10. expanf the file structure and select `d:\viostor\2k22\amd64` and click `ok`
11. you should see the Red Hat Virtio SCSI controller listed - if so click `next`.
12. now you can select the unallocated space and continue with install
13. when you can login to the OS install everything on the virtio CD using the istall application in the root of the CD
14. shutdown machine and change network type to virtio and GPU to VirtIO-GPU (and unmount virtio cd and install dvd) and reboot

## Configure for HA
1. in the gui select `Datacenter > HA`
2. click `add` in the resources pane
3. select `ClusterGroup1` (this was created in an ealier gist in this gist sequence)

## Test Live Migration
1. select the VM from pve1 node treet in the GUI
2. start the VM if it is not already started and wait fo bootstorm activity to subside
3. click `migrate` in the top right corner of the UI
4. select another node say `pve3` and  select `migrate` - note it should say online like the following:


<p align="center">
<img width="600" alt="image" src="../../assets/img/554c53e7712c.png">
</p>

Your vM should migrate in a minute or so at maximum with no errors.

## Test Failed Node
1. make sure your VM is started on pve3
2. pull the power on node pve3
3. watch it fail over in about 3 to 4 minutes
