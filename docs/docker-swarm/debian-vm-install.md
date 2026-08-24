---
title: "This file describes the network interfaces available on your system"
source_gist: https://gist.github.com/scyto/b714ba6ebacc15843d3d7a873ce9597e
---

This is the base of all my linux VM installs I use for docker etc

## Prep Hypervisor (instructions vary based on hypervisor so this is generic)
- Download netinst ISO from debian website
- Create a VM on your hypervsor 
- VM Machine Spec:
   - 200GB
   - 2 CPU
   - 4GB RAM
   - Attach to external network
- Boot from ISO

## Debian Install (hints)
- Non graphical Install debian with SSH and tools only (aka deslect everything else)
- Use the disk layout it reccomend unless you know what you are doing
- Create root and user <your-username> when prompted
- set a sensible machine name (i prefer docker01, docker02 etc if I am using this to host a docker swarm, you can use what you like, i will use this convention in the subsequent gists).
  
## First Login
Login as root on console, install basics

### Install Basics (updated for KVM based systems like proxmox or synology vmm)  
```  
apt-get update
apt-get upgrade
apt-get install nano sudo curl
apt-get install --no-install-recommends qemu-system libvirt-clients libvirt-daemon-system
```
### Make sure you can do sudo  
Add user to sudo group 

```
usermod -aG sudo <your-username>
```

### Configure Static IP ##
This is the recommended approach as network manager can cause rare issues with some containers.  I only saw issues with network manager and tailscale.
   
This assumes your ethernet adapter is eth0 in the VM, change as needed.

```
sudo nano /etc/network/interfaces   
```
- Edit `iface eth0 inet dhcp` and change to `iface eth0 inet static`
- add your static config (i prefer this approach as a failed DHCP server with static leases can't bring your swarm down...) as an example here is my complete file for my first node, you would increment the IP for each node.

```
  GNU nano 5.4                       /etc/network/interfaces *                                                                              
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
allow-hotplug eth0
iface eth0 inet static
 address 192.168.1.41
 netmask 255.255.255.0
 gateway 192.168.1.1
 dns-domain mydomain.com
 dns-nameservers 192.168.1.35 192.168.1.36

# This is an autoconfigured IPv6 interface
# iface eth0 inet6 auto   
```
 
- now reboot
   
# ALL STEPS FINISHED   
   
# **The steps below have been kept for archival purposes only. Do not use them.**    

# Why?  well i found that network manager interfered with a few container types   
   
#### Install network manager
```
sudo apt-get install network-manager
```   
   
#### Configure network manager   

```
sudo nano /etc/NetworkManager/NetworkManager.conf
```
   
- change the line managed=false to managed=true
- exit and save  

```
sudo nano /etc/network/interfaces
```
- Comment out all eth0 lines
- save and exit

```
sudo systemctl start NetworkManager
sudo systemctl enable NetworkManager
```
- Reboot now

## Network Manager configuration - Second Login
Login as youself from this point forward

Set eth0 to static IP address
```
sudo nmtui
 ```
Edit the connection, set your IP, gateway, DNS, and DNS search suffix to yourdomain.com
