---
title: "Enable IPv6 OSPF Routing on Thunderbolt-Net Mesh"
source_gist: https://gist.github.com/scyto/a3172c798cdaf12d33cd4efaeb6abe2c
---

# Enable IPv6 OSPF Routing on Thunderbolt-Net Mesh 
## This requires proxmox kernel 6.2.16-14-pve  or higher due to bugs in earlier version.s

This will result in a routable mesh network that can survive any one node failure or any one cable failure.
Alls the steps in this section *must be performed on each node*

## IPv6 OSPF connectivity over TB cluster network

### Enable IPv6 forwarding
Using IPv6 to take advantage of not needing to use addresses - does make things simpler 
-  uncomment `#net.ipv6.conf.all.forwarding=1` using `nano /etc/sysctl.conf` (remove the # symbol and save the file)

### Create Loopback interface
doing this means we don't have to give each thunderbolt a manual IPv6 addrees and that these addresses stay constant no matter what
Add the following to each node using `nano /etc/network/interfaces`

This should go uder the `auto lo` section and for each node the ::X should be 1, 2 or depending on the node 

```
auto lo:0
iface lo:0 inet static
        address fc00::X/128
```

so on the first node it would look comething like this:

```
...
auto lo
iface lo inet loopback
 
auto lo:0
iface lo:0 inet static
        address fc00::1/128
...
```

### Install OSPF (perform on all nodes)
1. Install Free Range Routing (FRR) `apt install frr`
2. Edit the FRR config file: `nano /etc/frr/daemons`
3. Adjust `ospf6d=no` to `ospf6d=yes`
4. save the file
5. restart the service with `systemctl restart frr`

### Configure OSPF (perforn on all nodes)
1. enter the FRR shell with `vtysh`
2. optionally show the current config with `show running-config`
3. enter the configure mode with `configure`
4. Apply the bellow configuration (it is possible to cut and paste this into the shell instead of typing it manually, you may need to press return to set the last !.  Also check there were no errors in repsonse to the paste text.).
Note: the X should be the number of the node you are working on, so for my stetup this would 0.0.0.1, 0.0.0.2 or 0.0.0.3.
```
ipv6 forwarding
!
router ospf6
 ospf6 router-id 0.0.0.X
 log-adjacency-changes
 exit
!
interface lo
 ipv6 ospf6 area 0
 exit
!
interface en05
 ipv6 ospf6 area 0
 ipv6 ospf6 network point-to-multipoint
 exit
!
interface en06
 ipv6 ospf6 area 0
 ipv6 ospf6 network point-to-multipoint
 exit
!

```
5. you may need to pres return after the last `!` to get to a new line - if so do this
6. exit the configure mode with the command `end`
7. save the configu with `write memory`
8. show the configure applied correctly with `show running-config` - note the order of the items will be different to how you entered them and thats ok.  (If you made a mistake i found the easiest way was to edt `/etc/frr/frr.conf` - but be careful if you do that.)
9. use the command `exit` to leave setup
10. rpeat steps 1 to 10 on the other 3 nodes
11. once you have configured all 3 nodes issue the command `show ipv6 ospf6 neighbor` you will see:
```
pve2# show ipv6 ospf6 neighbor
Neighbor ID     Pri    DeadTime    State/IfState         Duration I/F[State]
0.0.0.3           1    00:00:35     Full/PointToPoint    12:16:08 en05[PointToPoint]
0.0.0.1           1    00:00:33     Full/PointToPoint    12:16:02 en06[PointToPoint]
```
10. now issue the command `show ipv6 route` and you will see:
```
pve2# show ipv6 ospf6 neighbor
Neighbor ID     Pri    DeadTime    State/IfState         Duration I/F[State]
0.0.0.3           1    00:00:35     Full/PointToPoint    12:16:08 en05[PointToPoint]
0.0.0.1           1    00:00:33     Full/PointToPoint    12:16:02 en06[PointToPoint]
pve2# show ipv6 route
Codes: K - kernel route, C - connected, S - static, R - RIPng,
       O - OSPFv3, I - IS-IS, B - BGP, N - NHRP, T - Table,
       v - VNC, V - VNC-Direct, A - Babel, F - PBR,
       f - OpenFabric,
       > - selected route, * - FIB route, q - queued, r - rejected, b - backup
       t - trapped, o - offload failure

O>* fc00::1/128 [110/20] via fe80::f0:d6ff:fee3:aef1, en06, weight 1, 12:17:06
O   fc00::2/128 [110/10] is directly connected, lo, weight 1, 12:17:28
C>* fc00::2/128 is directly connected, lo, 12:17:28
O>* fc00::3/128 [110/20] via fe80::d5:6dff:fe74:5a0b, en05, weight 1, 12:17:10
C * fe80::/64 is directly connected, en06, 12:17:18
C * fe80::/64 is directly connected, vmbr0, 12:17:22
C>* fe80::/64 is directly connected, en05, 12:17:24
```
10. Exit the shell with `Exit`

Check networking with `lldpctl` you should see something like this, where you will see the two other nodes (note you may also see other devices on your network that are over the 2.5gbe proxmox management interface).

```
root@pve1:~# lldpctl
-------------------------------------------------------------------------------
LLDP neighbors:
-------------------------------------------------------------------------------
Interface:    en05, via: LLDP, RID: 1, Time: 0 day, 12:32:30
  Chassis:     
    ChassisID:    mac 48:21:0b:56:a5:d8
    SysName:      pve2.mydomain.com
    SysDescr:     Debian GNU/Linux 12 (bookworm) Linux 6.2.16-6-pve #1 SMP PREEMPT_DYNAMIC PMX 6.2.16-7 (2023-08-01T11:23Z) x86_64
    MgmtIP:       192.168.1.82
    MgmtIface:    4
    MgmtIP:       fc00::2
    MgmtIface:    1
    Capability:   Bridge, on
    Capability:   Router, on
    Capability:   Wlan, on
    Capability:   Station, off
  Port:        
    PortID:       mac 02:99:94:7c:11:48
    PortDescr:    en06
    TTL:          120
-------------------------------------------------------------------------------
Interface:    en06, via: LLDP, RID: 3, Time: 0 day, 12:31:58
  Chassis:     
    ChassisID:    mac 48:21:0b:58:9c:45
    SysName:      pve3.mydomain.com
    SysDescr:     Debian GNU/Linux 12 (bookworm) Linux 6.2.16-6-pve #1 SMP PREEMPT_DYNAMIC PMX 6.2.16-7 (2023-08-01T11:23Z) x86_64
    MgmtIP:       192.168.1.83
    MgmtIface:    4
    MgmtIP:       fc00::3
    MgmtIface:    1
    Capability:   Bridge, on
    Capability:   Router, on
    Capability:   Wlan, on
    Capability:   Station, off
  Port:        
    PortID:       mac 02:32:15:c8:5d:d4
    PortDescr:    en05
    TTL:          120
-------------------------------------------------------------------------------
```

You can now test the network by pinging FC00:: addresses of the other nodes (don't ping the node your on, and by pulling cables and seeing if it works).  Note routing changes can take 15s to take effect, I am not sure how to speed up that detection - but it will be an FRR conf setting or config setting I assume.  This is for future research task.

## Testing Example
-to be written- if bugs in debian / proxmox are fixed
