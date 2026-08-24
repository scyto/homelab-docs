---
title: "Give VMs Accesss to Ceph Mesh (routed not bridged access)"
source_gist: https://gist.github.com/scyto/dbbe5483f2779228ff743c5f333effe0
---

# Give VMs Accesss to Ceph Mesh (routed not bridged access)
## Version 0.9 (2025.04.29)


Routed is needed, you can't jut simply bridge en05 and en06 and have VMs work, bridging seems to not work on thundebolt interfaces, at least i could never get the interfaces working when bridged and it broke the ceph mesh completely.

tl;dr can't bridge thunderbolt interfaces

### Goal

Enable VMs hosted on proxmox to be able to access ceph mesh - my usecase is for my docker swarmVMs to be able store their bind mounts on cephFS

> ### Imperatives
>
> you **MUST** change your ceph public and private network in ceph.conf from `fc00::/64` to `fc00::80/124` if you do not ceph might get super funky as `fc00::/64` is actually treated as a /8 by ceph!? - this change should allow you have ceph mons `fc00:81 though fc00::8e`. Make sure to change, then reboot just one node and ensure all logs are clean before you move on

### Assumptions

- You already implemented [thunderbolt networking](cables-and-interfaces.md) and [frr setup](openfabric-mesh.md) as per those gists. Steps from them will not be re-documented here.
- Three Proxmox nodes: `pve1`, `pve2`, `pve3`
- Thunderbolt mesh links are : `en05` and `en06`
- No bridging of `en05` or `en06` is done - if these are bridged all mesh networking breaks, so never put them in a bridge!
- The openfabric mesh remains as-is for ceph traffic
- VMs are routed using vmbr100 on each node
- you have a true dual stack setup on your mesh (if you only have IPv4 including for ceph you drop the IPv6 sections)

REMEMBER ceph clients want to access the MONSs / OSDs /MGRs and MDSs on the `lo` interface loopback addresses - thats the goal!


---

### IP address and subnet info for new routed bridge.


| Node        | Interface  | Purpose         | IPv6 Address        | IPv4 Address       | MTU    |
|:-----------:|-----------:|:---------------:|:-------------------:|:------------------:|:------:|
| **pve1**    | `vmbr100`  | VM bridge       | `fc00:81::1/64`     | `10.0.81.1/24`     | 65520  |
| **pve2**    | `vmbr100`  | VM bridge       | `fc00:82::1/64`     | `10.0.82.1/24`     | 65520  |
| **pve3**    | `vmbr100`  | VM bridge       | `fc00:83::1/64`     | `10.0.83.1/24`     | 65520  |

---
## VM Bridge Setup 

This build on the work from the normal mesh gist and adds some additonal bridges to enable routing.

### Add a new bridge to each node for VMs to use
This bridge is what a VM will bind to that allows it to reach the ceph network, this bridge has no ports defined.

#### create a new file called `/etc/network/interfaces.d/vmbridge` for Node 1 (`pve1`).  Repeat on pve3 and pve3, changing addresses as per the table above.

```bash
# VM routed Bridge IPv4
auto vmbr100
iface vmbr100 inet static
    address 10.0.81.1/24
    mtu 65520
    bridge-ports none
    bridge-stp off
    bridge-fd 0

# VM routed Bridge IPv4
iface vmbr100 inet6 static
    address fc00:81::1/64
    mtu 65520
    bridge-ports none
    bridge-stp off
    bridge-fd 0

```
> **Notes:**
> - the MTU is set the same as thunderbolt interface MTUs - this is critical

---
## FRR Configuration addition repeat on node 2 & 3 with changes from table

Key things to note compared to the normal non-routed setup:
- additon of vmbr100 to openfabric to allow VM connectivity

#### add the following to `/etc/frr/frr.conf` for all 3 nodes.
(can be done by editing file or vtysh if you prefer)

```bash
!
interface vmbr100
 ip router openfabric 1
 ipv6 router openfabric 1
 openfabric passive
exit
!
```

- issue an `systemctl restart frr`
- you should see the new vmbr100 subnets appear in the routing table
- for example:

```
root@pve1 12:49:55 ~ # vtysh -c "show open topo"
Area 1:
IS-IS paths to level-2 routers that speak IP
 Vertex        Type         Metric  Next-Hop  Interface  Parent   
 -----------------------------------------------------------------
 pve1                                                             
 10.0.0.81/32  IP internal  0                            pve1(4)  
 10.0.81.0/24  IP internal  0                            pve1(4)  
 pve3          TE-IS        10      pve3      en05       pve1(4)  
 pve2          TE-IS        10      pve2      en06       pve1(4)  
 10.0.0.83/32  IP TE        20      pve3      en05       pve3(4)  
 10.0.83.0/24  IP TE        20      pve3      en05       pve3(4)  
 10.0.0.82/32  IP TE        20      pve2      en06       pve2(4)  
 10.0.82.0/24  IP TE        20      pve2      en06       pve2(4)  


IS-IS paths to level-2 routers that speak IPv6
 Vertex        Type          Metric  Next-Hop  Interface  Parent   
 ------------------------------------------------------------------
 pve1                                                              
 fc00::81/128  IP6 internal  0                            pve1(4)  
 fc00:81::/64  IP6 internal  0                            pve1(4)  
 pve3          TE-IS         10      pve3      en05       pve1(4)  
 pve2          TE-IS         10      pve2      en06       pve1(4)  
 fc00::83/128  IP6 internal  20      pve3      en05       pve3(4)  
 fc00:83::/64  IP6 internal  20      pve3      en05       pve3(4)  
 fc00::82/128  IP6 internal  20      pve2      en06       pve2(4)  
 fc00:82::/64  IP6 internal  20      pve2      en06       pve2(4)  


IS-IS paths to level-2 routers with hop-by-hop metric
 Vertex  Type  Metric  Next-Hop  Interface  Parent  
```

> **Notes:**
> - This enabled openfabric routing on the vmbr100 you created earlier
> - you wont see the IP address you added to vmbr100 - just the subet

---

## How to configure VM - Example for VM on node pve1

> - the vm has two interfaces, one bound to vmbr0 and one bound to vmbr100
> - this configuration is not intended to be migrated to other nodes (the guest adddressing is node specific)
>   - this could be mitigate through some use of an IPAM solution - unclear how yet
> - vm virtial nic attached to vmbr0 must be set in VM config **with MTU the same as vmbr0**
> - vm virtual nic attached to vmbr100 must be set in VM config **with MTU same as vmbr100**

Inside the routed VM (this is aVM on pve3):

```bash
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# This is a manuall configured interface fro the ceph mesh
allow-hotplug ens18
iface ens18 inet static
    address 10.0.83.105
    netmask 255.255.255.0
    gateway 10.0.83.1
    up ip route add 10.0.0.80/28 via 10.0.83.1 dev ens18

iface ens18 inet6 static
    address fc00:83::105
    netmask 64
    gateway fc00:83::1
    up ip -6 route add fc00::80/124 via fc00:83::1 dev ens18

# The primary network interface
auto ens19
iface ens19 inet auto

iface ens19 inet6 auto
   accept_ra 1
   autoconf 1
   dhcp 1
   
```

> **Notes:**
> - uses `vmbr100` on the host to access the mesh
> - uses `vmb0` on the host to access the internet
> - static routes defined via `fc00:83::1` and `10.0.83.1` in the VM (using up command) to avoid using the defatul route on vmbr0
>   - while it may work without these i found some error situations where connecvity failed due to their being two default routes - maybe someone can suggest more elegant fix
> - the IPv4 and IPv6 addresses need to be from the hosts vmbr100 /24 and /64 ranges.

You can now test pinging from the VM to various node and ceph addresses.

Now you need to setup ceph client in the vm - coming soon.

---
### Example frr.conf from my pve1 node after this gist.

<details>
  <summary>Click me</summary>

```
root@pve1 13:19:03 ~ # cat /etc/frr/frr.conf
frr version 8.5.2
frr defaults datacenter
hostname pve1
log syslog informational
service integrated-vtysh-config

interface en05
 ip router openfabric 1
 ipv6 router openfabric 1
 openfabric hello-interval 1
 openfabric hello-multiplier 3
 openfabric csnp-interval 5
 openfabric psnp-interval 2
exit

interface en06
 ip router openfabric 1
 ipv6 router openfabric 1
 openfabric hello-interval 1
 openfabric hello-multiplier 3
 openfabric csnp-interval 5
 openfabric psnp-interval 2
exit

interface lo
 ip router openfabric 1
 ipv6 router openfabric 1
 openfabric passive
exit

interface vmbr100
 ip router openfabric 1
 ipv6 router openfabric 1
 openfabric passive
exit

router openfabric 1
 net 49.0000.0000.0081.00
 lsp-gen-interval 5
exit
```
 </details>

---
### Example interfaces file from a VM on my pve1 node after this gist.
note this is for VMs running ifupdown2 instead of networking.service
i had to install ifupown2 in my debian swarm vms as an upgrade from from 11 to 12 didn't not automatically make this switch!

<details>
  <summary>Click me</summary>
    
```bash
auto eth0
allow-hotplug eth0
iface eth0 inet static
  address 192.168.1.41
  netmask 255.255.255.0
  gateway 192.168.1.1
  dns-domain mydomain.com
  dns-search mydomain.com
  dns-nameservers 192.168.1.5  192.168.1.6

iface eth0 inet6 static
  accept_ra = 2
  address 2001:db8:1000:1::41
  netmask 64
  gateway 2001:db8:1000:1::1
  dns-domain mydomain.com
  dns-search mydomain.com
  dns-nameservers 2001:db8:1000:1::5 2001:db8:10001::6


# This is a manuall configured interface fro the ceph mesh
auto eth1
allow-hotplug eth1
iface eth1 inet static
  address 10.0.81.41
  netmask 255.255.255.0
#  gateway 10.0.81.1 - not strictly needed, causes issues on ifreload based systems
  up ip route add 10.0.0.80/28 via 10.0.81.1 dev eth1 || true

iface eth1 inet6 static
  address fc00:81::41
  netmask 64
#  gateway fc00:81::1  - not strictly needed, causes issues on ifreload based systems
  up ip -6 route add fc00::80/124 via fc00:81::1 dev eth1 || true
``` 
    
</details>
