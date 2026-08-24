---
title: "Enable Dual Stack (IPv4 and IPv6) OpenFabric Routing"
source_gist: https://gist.github.com/scyto/58b5cd9a18e1f5846048aabd4b152564
comments: true
---

#  Enable Dual Stack (IPv4 and IPv6) OpenFabric Routing

## Version 2.5 (2025.04.27) 

[this gist is part of this series](../index.md)

This assumes you are running Proxmox 8.4 and that the line `source /etc/network/interfaces.d/*` is at the end of the interfaces file (this is automatically added to both new and upgraded installations of Proxmox 8.2).

This changes the previous file design thanks to @NRGNet and @tisayama to make the system much more reliable in general, more maintainable esp for folks using IPv4 on the private cluster network ~(i still recommend the use of the IPv6 FC00 network you will see in these docs)~

Notable changes from original version [here](openfabric-mesh-legacy.md)

- ~move IP address configuration from `interfaces.d/thundebolt` to frr configuration~ i reverted this on 2025.04.27 and improved settings  in interfaces.d/thunderbolt based on recommendations from chatGPT to solve issues i hit it my routed network setup (coming soon)
- new approach to remove dependecy on post-up with new scripts in if-up.d that logs to systemlog
- reminder to copy frr.conf > frr.conf.local to prevent breakage if you enable Proxmox SDN
- dependent on the changes to the udev link scripts [here](cables-and-interfaces.md#set-interfaces-to-up-on-reboots-and-cable-insertions)

This will result in an IPv4 and IPv6 routable mesh network that can survive any one node failure or any one cable failure. Alls the steps in this section must be performed on each node

> ** NOTES on Dual Stack*
> 
> Having spent 3 days hammering my network and playing with various different routed toplogies i am of the current opinion
> - i still prefer IPv6 for my mesh but if you setup for IPv4 it should now be fine but my gists will continue to assume you used IPv6 for ceph
> - i have no opinion on squid and dual stack yet - should be doable... we will seee
> - if you use ONLY IPv6 for the love-of-god(tm) make sure that `ms_bind_ipv4 = false` is set in ceph.conf or really bad things will eventuall happen


## Defining thunderbolt network

> This was revised on 2025.04.27 to move loopback IP addressing back from frr.conf to here (along with some reliability changes recommended by chatgpt) having loopback IPs was a stupid idea as they should be up irrespective of the state of the mesh to allow ceph processes to start binding to it.

Create a new file using `nano /etc/network/interfaces.d/thunderbolt` and populate with the following


```bash
# Thunderbolt interfaces for pve1 (Node 81)

auto en05
iface en05 inet6 static
    pre-up ip link set $IFACE up
    mtu 65520

auto en06
iface en06 inet6 static
    pre-up ip link set $IFACE up
    mtu 65520

# Loopback for Ceph MON
auto lo
iface lo inet loopback
    up ip -6 addr add fc00::81/128 dev lo
    up ip addr add 10.0.0.81/32 dev lo
```
> **Notes:**
> - doing loopback IP is more reliable in interfaces file than in frr.conf the ip address will always be available for the mon, mgr, and mds processes of ceph to bind to irrespective of frr service status
> - mtus are super importantor BGP and openfabric seem to have node to node negotiation issues
> - the `pre-up` and `up` directives were recommended by chatGPT to ensure the interfaces are up before applying the IP address and MTU - should make things more reliable


## Enable IPv4 and IPv6 forwarding
1. use `nano /etc/sysctl.d/local.conf` to open the file (if it doesn't exist create it and add the lines below)
2. uncomment `#net.ipv6.conf.all.forwarding=1` (remove the # symbol)
3. uncomment `#net.ipv4.ip_forward=1` (remove the # symbol)
4. save the file
5. issue `reboot now` for a complete reboot

## FRR Setup

### Install & enable FRR (not needed on proxmox 8.4+ )
1. Install Free Range Routing (FRR) `apt install frr`
2. Enable frr `systemctl enable frr`

### Enable the fabricd daemon

1. edit the frr daemons file (`nano /etc/frr/daemons`) to change `fabricd=no` to `fabricd=yes` 
2. save the file
3. restart the service with `systemctl restart frr`

### Mitigate FRR Timing Issues (I need someone with an MS-101 to confirm if helps solve their IPv4 issues)

#### create script that is automatically processed when en05/en06 are brougt up to restart frr

> **notes**
> - this should make IPv4 more stable for all users (i ended up seeing IPv4 issues too, just less commonly than MS-101 users)
> - i found the chnages i introduced in 2.5 version of this gist make this less needed, occasionally ifreload / ifupdown2 may cause enough changes that frr gets restarted too often and the service will need to be unblocked with systemctl.


1. create a new file with `nano /etc/network/if-up.d/en0x`
2. add to file the following

```
#!/bin/bash
# note the logger entries log to the system journal in the pve UI etc

INTERFACE=$IFACE

if [ "$INTERFACE" = "en05" ] || [ "$INTERFACE" = "en06" ]; then
    logger "Checking if frr.service is running for $INTERFACE"
    
    if ! systemctl is-active --quiet frr.service; then
        logger -t SCYTO "   [SCYTO SCRIPT ] frr.service not running. Starting service."
        if systemctl start frr.service; then
            logger -t SCYTO "   [SCYTO SCRIPT ] Successfully started frr.service"
        else
            logger -t SCYTO "   [SCYTO SCRIPT ] Failed to start frr.service"
        fi
        exit 0
    fi

    logger "Attempting to reload frr.service for $INTERFACE"
    if systemctl reload frr.service; then
        logger -t SCYTO "   [SCYTO SCRIPT ] Successfully reloaded frr.service for $INTERFACE"
    else
        logger -t SCYTO "   [SCYTO SCRIPT ] Failed to reload frr.service for $INTERFACE"
    fi
fi
```

3. make it executable with `chmod +x /etc/network/if-up.d/en0x`

### mitgigate issues cause by things that reset the loopback
#### create script that is automatically processed when lo is reprocessed by ifreload, ifupdown2, pve set, etc

1. create a new file with `nano /etc/network/if-up.d/lo`
2. add to file the following

```
#!/bin/bash

INTERFACE=$IFACE

if [ "$INTERFACE" = "lo" ]  ; then
    logger "Attempting to restart frr.service for $INTERFACE"
    if systemctl restart frr.service; then
        logger -t SCYTO "   [SCYTO SCRIPT ] Successfully restart frr.service for $INTERFACE"
    else
        logger -t SCYTO "   [SCYTO SCRIPT ] Failed to restart frr.service for $INTERFACE"
    fi
fi
```
make it executable with `chmod +x /etc/network/if-up.d/lo`

### Configure OpenFabric (perforn on all nodes)

**note: if (and only if) you have already configured SDN you should make these settings in /etc/frr/frr.conf.local and reapply your SDN configuration to have SDN propogate these into frr.conf (you can also make the edits to both files if you prefer) if you make these edits to only frr.conf with SDN active and then reapply the settings it will loose these settings.

1. enter the FRR shell with `vtysh`
2. optionally show the current config with `show running-config`
3. enter the configure mode with `configure`
4. Apply the bellow configuration (it is possible to cut and paste this into the shell instead of typing it manually, you may need to press return to set the last !.  Also check there were no errors in repsonse to the paste text.).

**Note: the X should be the number of the node you are working on** For example node 1 would use 1 in place of X
```
ip forwarding
ipv6 forwarding

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
 openfabric hello-interval 1
 openfabric hello-multiplier 3
 openfabric csnp-interval 5
 openfabric psnp-interval 2
 openfabric passive
exit

router openfabric 1
net 49.0000.0000.000x.00
lsp-gen-interval 5
exit
!
exit

```
5. you may need to press return after the last `exit` to get to a new line - if so do this
6. save the configu with `write memory`
7. show the configure applied correctly with `show running-config` - note the order of the items will be different to how you entered them and thats ok.  (If you made a mistake i found the easiest way was to edt `/etc/frr/frr.conf` - but be careful if you do that.)
8. use the command `exit` to leave setup
9. repeat steps 1 to 9 on the other 3 nodes
10. once you have configured all 3 nodes issue the command `vtysh -c "show openfabric topology"` if you did everything right you will see (note it may take 45 seconds for for all routes to show if you just restarted frr for any reason):
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

### IMPORTAT - you need to do this to stop SDN breaking you in future 
if all is working issue a `cp /etc/frr/frr.conf /etc/frr/frr.conf.local` this is because when enabling proxmox SDN proxmox will overwrite frr.conf - however it will read the .local file and apply that.

**note: if you already have SDN configured do not do the step above as you will mess both your SDN and this openfabric topology (see note at start of frr instructions)

based on this response https://forum.proxmox.com/threads/relationship-of-frr-conf-and-frr-conf-local.165465/ if you have SDN all local (non SDN) configuration changes should be made in .local, this should be read next time SDN apply is used. do not copy frr.conf > frr.conf.local after doing anything with SDN or when you tear down SDN the settings will not be removed from frr.conf
