---
title: "Migrating Home Assistant OVA VM from Hyper-V to Proxmox"
source_gist: https://gist.github.com/scyto/96ee39f432f18a43ea3b95697c3f398e
---

# Migrating Home Assistant OVA VM from Hyper-V to Proxmox
Now that i have nailed the qm *disk* import command and given all linux kernel have the virtio drivers in them after 5.6 this *should* be a breeze!

## Export
Export VHD from Hyper-V into share proxmox can see (tbh at this point if you don't know how...)

## Create VM on proxmox
I created a 4GB VM with no disks at all andthe virtio network.
Make sure you connect it to a live bridge or hass will hand at starting network manager
I added a TPM drive
I added a U?EFI drive buy unchecked enroll keys (if you forget this the VM will not boot)


## Import disk
`qm disk import 106 nameofile.vhdx vDisks` (imports disk for VM 106 and puts it on my volume called vDisks)

## Configure VM with disk
attach the unsued disk
make it virtio 0 with whatever settings you like (i enable discard and write through)

## Boot VM Machine
It should boot just fine

## Change IP address back to whaetver you were using 
As adapter changed set hass settings back to original static IP you were using a at hassos console.
This means if you were using static you will need to do the instructions below.
If you use a DHCP reseveration a) why are you doing that for crtitical machines... dhcp goes down your crtitical machines go down.. b) instead of doing instructions below you can give the network card for the vm in proxmox same MAC as the reservation already has!

```
ha > login

# nmcli con show
# nmcli con edit “HassOS default” (or whatever the active connection is calle don you machine 

nmcli> set ipv4.addresses 192.168.1.63/24
nmcli> set ipv4.dns 1.1.1.1
nmcli> set ipv4.gateway 192.168.1.1
nmcli> save
nmcli> quit

# reboot now
```
