---
title: "THIS GIST IS NOW DEPRECATED NEW ONE IS AVAILABLE [HERE](openfabric-mesh.md) I WONT BE UPDATING THIS ONE OR REPLYING TO COMMENTS ON THIS ONE (COMMENTS NOW DISABLED)."
source_gist: https://gist.github.com/scyto/4c664734535da122f4ab2951b22b2085
---

# THIS GIST IS NOW DEPRECATED NEW ONE IS AVAILABLE [HERE](openfabric-mesh.md) I WONT BE UPDATING THIS ONE OR REPLYING TO COMMENTS ON THIS ONE (COMMENTS NOW DISABLED).


# Enable Dual Stack (IPv4 and IPv6) OpenFabric Routing

[this gist is part of this series](../index.md)

This assumes you are running Proxmox 8.2 and that the line `source /etc/network/interfaces.d/*` is at the end of the interfaces file (this is automatically added to both new and upgraded installations of Proxmox 8.2).

This changes the previous file design thanks to @NRGNet for the suggestions to move thunderbolt settings to a file in /etc/network/interfaces.d  it makes the system much more reliable in general, more maintainable esp for folks using IPv4 on the private cluster network (i still recommend the use of the IPv6 FC00 network you will see in these docs)

This will result in an IPv4 and IPv6 routable mesh network that can survive any one node failure or any one cable failure. Alls the steps in this section must be performed on each node

## NOTES on Dual Stack
I have included this for completeness, i only run the FC00:: IPv6 network as ceph does not support dual stack, i strongly recommend you consider only using IPv6.  For example for ceph do not dual stack - either use IPv4 or IPv6 addressees for all the monitors, MDS and daemons - despite the docs implying it is ok my findings on quincy are is it is funky.... 


## Defining thunderbolt network

Create a new file using `nano /etc/network/interfaces.d/thunderbolt` and populate with the following
Remember X should match you node number, so for example 1,2 or 3.

```
auto lo:0
iface lo:0 inet static
        address 10.0.0.8X/32
        
auto lo:6
iface lo:6 inet static
        address fc00::8X/128
        
allow-hotplug en05
iface en05 inet manual
        mtu 65520

allow-hotplug en06
iface en06 inet manual
        mtu 65520
```
Save file, repeat on each node.

## Enable IPv4 and IPv6 forwarding
1. use `nano /etc/sysctl.conf` to open the file
2. uncomment `#net.ipv6.conf.all.forwarding=1` (remove the # symbol)
3. uncomment `#net.ipv4.ip_forward=1` (remove the # symbol)
4. save the file
5. issue `reboot now` for a complete reboot

## FRR Setup

### Install FRR
Install Free Range Routing (FRR) `apt install frr`

### Enable the fabricd daemon

1. edit the frr daemons file (`nano /etc/frr/daemons`) to change `fabricd=no` to `fabricd=yes` 
2. save the file
3. restart the service with `systemctl restart frr`

### Mitigate FRR Timing Issues at Boot

#### Add post-up command to /etc/network/interfaces
sudo nano `/etc/network/interfaces`

Add `post-up /usr/bin/systemctl restart frr.service`as the _last_ line in the file (this should go after the line that starts `source`)

#### NOTE for Minisforum MS-01 users
make the post-up line above read `post-up sleep 5 && /usr/bin/systemctl restart frr.service` instead 
this has been verified to be required due to timing issues see on those units, exact cause unknown, may be needed on other hardware too.



### Configure OpenFabric (perforn on all nodes)
1. enter the FRR shell with `vtysh`
2. optionally show the current config with `show running-config`
3. enter the configure mode with `configure`
4. Apply the bellow configuration (it is possible to cut and paste this into the shell instead of typing it manually, you may need to press return to set the last !.  Also check there were no errors in repsonse to the paste text.).

**Note: the X should be the number of the node you are working on, as an example -  0.0.0.1, 0.0.0.2 or 0.0.0.3.**
```
ip forwarding
ipv6 forwarding
!
interface en05
ip router openfabric 1
ipv6 router openfabric 1
exit
!
interface en06
ip router openfabric 1
ipv6 router openfabric 1
exit
!
interface lo
ip router openfabric 1
ipv6 router openfabric 1
openfabric passive
exit
!
router openfabric 1
net 49.0000.0000.000X.00
exit
!

```
5. you may need to pres return after the last `!` to get to a new line - if so do this
6. exit the configure mode with the command `end`
7. save the configu with `write memory`
8. show the configure applied correctly with `show running-config` - note the order of the items will be different to how you entered them and thats ok.  (If you made a mistake i found the easiest way was to edt `/etc/frr/frr.conf` - but be careful if you do that.)
9. use the command `exit` to leave setup
10. repeat steps 1 to 9 on the other 3 nodes

11. once you have configured all 3 nodes issue the command `vtysh -c "show openfabric topology"` if you did everything right you will see:
```
Area 1:
IS-IS paths to level-2 routers that speak IP
Vertex               Type         Metric Next-Hop             Interface Parent
pve1                                                                  
10.0.0.81/32         IP internal  0                                     pve1(4)
pve2                 TE-IS        10     pve2                 en06      pve1(4)
pve3                 TE-IS        10     pve3                 en05      pve1(4)
10.0.0.82/32         IP TE        20     pve2                 en06      pve2(4)
10.0.0.83/32         IP TE        20     pve3                 en05      pve3(4)

IS-IS paths to level-2 routers that speak IPv6
Vertex               Type         Metric Next-Hop             Interface Parent
pve1                                                                  
fc00::81/128         IP6 internal 0                                     pve1(4)
pve2                 TE-IS        10     pve2                 en06      pve1(4)
pve3                 TE-IS        10     pve3                 en05      pve1(4)
fc00::82/128         IP6 internal 20     pve2                 en06      pve2(4)
fc00::83/128         IP6 internal 20     pve3                 en05      pve3(4)

IS-IS paths to level-2 routers with hop-by-hop metric
Vertex               Type         Metric Next-Hop             Interface Parent

```
Now you should be in a place to ping each node from evey node across the thunderbolt mesh using IPv4 or IPv6 as you see fit.

# THIS GIST IS NOW DEPRECATED NEW ONE IS AVAILABLE [HERE](openfabric-mesh.md) I WONT BE UPDATING THIS ONE OR REPLYING TO COMMENTS ON THIS ONE (COMMENTS NOW DISABLED).
