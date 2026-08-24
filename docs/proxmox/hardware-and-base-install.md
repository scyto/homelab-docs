---
title: "Hardware Setup / Proxmox Base Install"
source_gist: https://gist.github.com/scyto/cd1a8cdd9904f43e319e438551d7f92c
---

# Hardware Setup / Proxmox Base Install

[this gist is part of this series](index.md)

## Hardware Setup (perform on all 3 nodes)
- Connect all 3 NUC to power etc
- Disable secure boot in BIOS on all nodes
- Connect all 3 TB4 cables in a rinng topology:
```
using the numbers printed on the case of the intel13 nucs connect cables as follows (this is important):
- node 1 port 1 > node 2 port 2
- node 2 port 1 > node 3 port 2
- node 3 port 1 > node 1 port 2
```
- Prepare bootable usb key by downloading proxmox iso and tools such as 'rufus'
- Boot from USB

## Proxmox Base Install (repeat on each node)
- choose GUI (why not!)
- accept terms
- choose the SSD *NOT* the NVME for the install
- set country, keyboard, etc
- choose a password (this will be for the user - root) and set email
- choose enp86s0 as the management interface (on proxmox 8 you will see the thundebolt netwrok too if cables are connected)
- set a name for each node - i used `pveX.mydomain.com` where X = the node number i wanted
- set fixed IPv4 address for the management network
    - 192.168.1.81/24 for node 1
    - 192.168.1.82/24 for node 2
    - 192.168.1.83/24 for node 3
- set external DNS server and gateway 
- let the software partition disk as it sees fit
- review summary page
- removed the USB key and reboot when prompted

You should now have 3 nodes.  Each should be accessible over the network with the IP addresses you specified. e.g 192.168.1.81:8006, 192.168.1.82:8006, 192.168.1.83:8006

The default username is root and you use the password you defined earlier.  Consider making constrained users and doing security properly.  I won't be doing that, i will be using root as this a PoC.

## Set Package Repositories (only needed if you don't use a subscription)
*Note:* i will not be using enterprise packages as this is a PoC for evaluation / homeLab purposes only

In `node-name > updates > repositories` perform the following:
- add `No-Subscription`
- add `Ceph Quincy No-Subscription`
- disable `pve-enterprise`
- disable `ceph-quincy enterprise` too

Open the shell and perform `apt update && apt upgrade` to update all components and then reboot.
