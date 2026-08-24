---
title: "Enable any LAN client to access mesh"
source_gist: https://gist.github.com/scyto/c0df83c269c5f5c192cb8a08a0d4a559
---

# Enable any LAN client to access mesh
## Version 0.5 (2025.04.29)

I have other devices that need to access the ceph mesh that are on my LAN.  This gist is only needed if you want LAN clients to access the ceph mesh.

## Goals
- let any client on LAN access the mesh
- avoid setting static routes on my router
- enable support for routing topology changes without having to reconfigure router

REMEMBER ceph clients want to access the MONSs / OSDs / MGRs and MDSs on the `lo` interface loopback addresses - thats the goal!

## Overview
- BGP is used to advertise routes for both LAN based clients and VM based clients
- BGP P2P links have to be used as other BGP mechnanisms didn't seem to work
- BGP routes are explictly defined for dvertisement, no broadcast is used

## Asumptions
- Ubiquiti unifi OS router with BGP feature (EFG and maybe others)
- all previous gists have been followed and are working perfectly, this will only detail changes to the overall setup
- you have a true dual stack setup on your LAN (if you only have IPv4 including for ceph you drop the IPv6 sections)

---

## FRR BGP pve node Settings 
| Field             | pve1                    | pve2                    | pve3                    |
|:-----------------:|:-----------------------:|:-----------------------:|:-----------------------:|
| BGP Router-ID     | `192.168.1.81`            | `192.168.1.82`            | `192.168.1.83`            |
| BGP ASN           | `65001`                 | `65001`                 | `65001`                 |  
| IPv6 Neighbors<br>(Node LAN IP)    | `2001:db8:1000:1::82`<br> `2001:db8:1000:1::83`<br>`2001:db8:1000:1::1` |`2001:db8:1000:1::81`<br> `2001:db8:1000:1::83`<br>`2001:db8:1000:1::1` | `2001:db8:1000d:1::81`<br> `2001:db8:1000:1::82`<br>`d2001:db8:1000:1::1` | 
| IPv4 Neighbors<br>(Node LAN IP)    | `192.168.1.82`<br>`192.168.1.83`<br>`192.168.1.1`|`192.168.1.81`<br>`192.168.1.83`<br> `192.168.1.1`|`192.168.1.81`<br>`192.168.1.82`<br>`192.168.1.1`|
| IPv6 Routes<br>(mesh network)       |`fc00::81/128`<br>`fc00:81::/64`|`fc00::82/128`<br>`fc00:82::/64`|`fc00::83/128`<br>`fc00:83::/64`     |
| IPv4 Routes<br>(mesh network)| `10.0.0.81/32`<br>`10.0.81.0/24`| `10.0.0.82/32`<br>`10.0.82.0/24`| `10.0.0.83/32`<br>`10.0.83.0/24` |

> **notes 
> - `2001:db8:1000:1::` is not my real subnet, `2001:db8::` is a subnet resevered for documentation
> - you should use your subnet addresses as appropriate


---
## Network Prep

1. Find out the MTU your router uses - in my case it is 9182
2. Ensure same MTU is set on vmbr0 - this can be done in the proxmox gui or by setting `mtu 9182` in the `/etc/network/interfaces` in the vmbr0 stanza.

## Enable each node to advertise routes to the LAN.

### Enable BGP daemon
1. nano `/etc/frr/daemons` change `bgpd=no` to `bgpd=yes` and save the file
2. then `systemctl reload frr` 

### Add BGP confing to frr.conf (node `pve1` example)

> use the settings from the table above and remember to change them as needed for each node

1. add this to `frr.conf` and restart frr

```
router bgp 65001
 bgp router-id 192.168.1.81
 no bgp ebgp-requires-policy
 neighbor 2001:db8:1000:1::82 remote-as 65001
 neighbor 2001:db8:1000:1::83 remote-as 65001
 neighbor 2001:db8:1000:1::1 remote-as 65001
 neighbor 192.168.1.82 remote-as 65001
 neighbor 192.168.1.83 remote-as 65001
 neighbor 192.168.1.1 remote-as 65001

 address-family ipv6 unicast
  network fc00::81/128
  network fc00:81::/64
  neighbor 2001:db8:1000:1::82 activate
  neighbor 2001:db8:1000:1::83 activate
  neighbor 2001:db8:1000:1::1 activate
 exit-address-family

 address-family ipv4 unicast
  network 10.0.0.81/32
  network 10.0.81.0/24
  neighbor 192.168.1.82 activate
  neighbor 192.168.1.83 activate
  neighbor 192.168.1.1 activate
 exit-address-family
 ```
> Remember to change the IP addreses to match the table above the easy way to think about this is:
>  - network = subnets on this node i want to advertise
>  - neighbor = other routers/nodes i have to talk to
>    
> Instead of explicitly defining the networks you could use one line that says `redistribute connected` in place of the two `network` values in each familly.
> This would advetise all learnt routes (not kernel / static routes) to your router.  
> I think this would be a better way as there is less reconfiguration.
> But given the unpredictably of this in different peoples environments I elected to explicitly define the routes for predictability.



## Ubiuiti UnifiOS Router Integration

This has only be tested on an EFG running network app 9.1.92

### Router Settings
|       Field      | Value         |
|:-----------------|:-------------:|
| BGP ASN          | `65001`       |
| BGP Router ID    | `192.168.1.1` |
| IPv4 LAN Address | `192.168.1.1` |
| IPv6 LAN Address | 2001:db8:1000:1::1/64 |

> **notes
> - the BGP AS must be in the range of `64512-65534` or your ISP will get very cross at you ;-)
> - the BGP Router ID can be anything really, convention makes it the router IPv4 address
> - The LAN addresses are you normal LAN addresses of you routers LAN port

### Prepare a BGP conf file for upload to Unifi OS

Remember to use something that uses linux text formatting.

```bash
router bgp 65001
 bgp router-id 192.168.1.1
 no bgp ebgp-requires-policy

 neighbor 192.168.1.81 remote-as 65001
 neighbor 192.168.1.81 update-source 192.168.1.1
 neighbor 192.168.1.81 next-hop-self

 neighbor 192.168.1.82 remote-as 65001
 neighbor 192.168.1.82 update-source 192.168.1.1
 neighbor 192.168.1.82 next-hop-self

 neighbor 192.168.1.83 remote-as 65001
 neighbor 192.168.1.83 update-source 192.168.1.1
 neighbor 192.168.1.83 next-hop-self

 neighbor 2001:db8:1000:1::81 remote-as 65001
 neighbor 22001:db8:1000:1::81 update-source 2001:db8:1000:1::1

 neighbor 2001:db8:1000:1::82 remote-as 65001
 neighbor 22001:db8:1000:1::82 update-source 2001:db8:1000:1::1

 neighbor 2001:db8:1000:1::83 remote-as 65001
 neighbor2001:db8:1000:1::83 update-source 2001:db8:1000:1::1

 address-family ipv6 unicast
  neighbor 2001:db8:1000::81 activate
  neighbor 2001:db8:1000:1::81 next-hop-self
  neighbor 22001:db8:1000:1::82 activate
  neighbor 2001:db8:1000:1::82 next-hop-self
  neighbor 2001:db8:1000:1::83 activate
  neighbor 2001:db8:1000:1::83 next-hop-self
 exit-address-family

 address-family ipv4 unicast
  neighbor 192.168.1.81 activate
  neighbor 192.168.1.81 next-hop-self
  neighbor 192.168.1.82 activate
  neighbor 192.168.1.82 next-hop-self
  neighbor 192.168.1.83 activate
  neighbor 192.168.1.83 next-hop-self
 exit-address-family
```

> **note 
> - the format above is ordered for easy reading `vtysh -c "show running-config"` will show a different layout
> - the settings above wont be written to `/etc/frr/frr.conf` - so don't worry if thats empty

### Upload to the Unifi OS router

1. in unifi network application go to `settings > routing > bgp`
2. name = ceph-mesh
3. device = name of router (should be on the drop down)
4. click upload and upload file
5. do NOT select the check box `override wan monitors` (uncheck it it is checked)

> **Notes:**
> - I found some times times frr.service can crash on UI whem you upload, if it does just restart it
> - The router learns `fc00::8x/128`, `fc00:8x::/64`, `10.0.0.8x/32`, and `10.0.8x.0/24` routes from your the nodes.
> - you can use the following command to check everything looks good:
>   - `vtysh -c "show bgp ipv6 unicast summary"`
>   - `vtysh -c "show bgp ipv4 unicast summary"`

it will look something like this:

> note the i infront of the IPv6 addresses is just a known display bug in frr 8.1 that my router is running

```
root@EFG:/etc/frr# vtysh -c "show bgp ipv6 unicast"
BGP table version is 6, local router ID is 192.168.1.1, vrf id 0
Default local pref 100, local AS 65001
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*>ifc00::81/128     fe80::4a21:bff:fe58:9c45
                                             0    100      0 i
*>ifc00::82/128     fe80::4a21:bff:fe56:a5d8
                                             0    100      0 i
*>ifc00::83/128     fe80::4a21:bff:fe56:a650
                                             0    100      0 i
*>ifc00:81::/64     fe80::4a21:bff:fe58:9c45
                                             0    100      0 i
*>ifc00:82::/64     fe80::4a21:bff:fe56:a5d8
                                             0    100      0 i
*>ifc00:83::/64     fe80::4a21:bff:fe56:a650
                                             0    100      0 i

Displayed  6 routes and 6 total paths
root@EFG:/etc/frr# vtysh -c "show bgp ipv4 unicast"
BGP table version is 6, local router ID is 192.168.1.1, vrf id 0
Default local pref 100, local AS 65001
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*>i10.0.0.81/32     192.168.1.81             0    100      0 i
* i                 192.168.1.81             0    100      0 i
*>i10.0.0.82/32     192.168.1.82             0    100      0 i
* i                 192.168.1.82             0    100      0 i
*>i10.0.0.83/32     192.168.1.83             0    100      0 i
* i                 192.168.1.83             0    100      0 i
*>i10.0.81.0/24     192.168.1.81             0    100      0 i
* i                 192.168.1.81             0    100      0 i
*>i10.0.82.0/24     192.168.1.82             0    100      0 i
* i                 192.168.1.82             0    100      0 i
*>i10.0.83.0/24     192.168.1.83             0    100      0 i
* i                 192.168.1.83             0    100      0 i

Displayed  6 routes and 12 total paths
``` 
---
# Bonus Tip: Monitor Convergence

If you don't see the right things above see double check the router can see its neighbors wth `vtysh -c "show bgp sum"` you should get something like this:

```
IPv4 Unicast Summary (VRF default):
BGP router identifier 192.168.1.1, local AS number 65001 vrf-id 0
BGP table version 6
RIB entries 11, using 2024 bytes of memory
Peers 6, using 4338 KiB of memory

Neighbor                  V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
pve1(192.168.1.81)        4      65001        86        85        0    0    0 00:04:09            2        0 N/A
pve2(192.168.1.82)        4      65001        86        85        0    0    0 00:04:08            2        0 N/A
pve3(192.168.1.83)        4      65001        86        85        0    0    0 00:04:08            2        0 N/A
pve1(2001:db8:1000:1::81) 4      65001        88        86        0    0    0 00:04:09            2        0 N/A
pve2(2001:db8:1000:1::82) 4      65001        88        86        0    0    0 00:04:08            2        0 N/A
pve3(2001:db8:1000:1::83) 4      65001        88        86        0    0    0 00:04:08            2        0 N/A

Total number of neighbors 6

IPv6 Unicast Summary (VRF default):
BGP router identifier 192.168.1.1, local AS number 65001 vrf-id 0
BGP table version 6
RIB entries 11, using 2024 bytes of memory
Peers 3, using 2169 KiB of memory

Neighbor                  V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
pve1(2001:db8:1000:1::81) 4      65001        88        86        0    0    0 00:04:09            2        0 N/A
pve2(2001:db8:1000:1::82) 4      65001        88        86        0    0    0 00:04:08            2        0 N/A
pve3(2001:db8:1000:1::83) 4      65001        88        86        0    0    0 00:04:08            2        0 N/A

Total number of neighbors 3
```

If you seen nothing or something missing the mostly like issues are:
1. MTU mismatch between br0 on the router and vmbr0 on the proxmox nodes
2. a firewall blocking BGP packets somehwere

---
Example frr.conf after these changes (this is from my pve1)

<details>
  <summary>Click me</summary>
 
```
root@pve1 16:29:49 ~ # cat  /etc/frr/frr.conf
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

router bgp 65001
 bgp router-id 192.168.1.81
 no bgp ebgp-requires-policy
 neighbor 2600:a801:830:1::82 remote-as 65001
 neighbor 2600:a801:830:1::83 remote-as 65001
 neighbor 2600:a801:830:1::1 remote-as 65001
 neighbor 192.168.1.82 remote-as 65001
 neighbor 192.168.1.83 remote-as 65001
 neighbor 192.168.1.1 remote-as 65001

 address-family ipv6 unicast
  network fc00::81/128
  network fc00:81::/64
  neighbor 2600:a801:830:1::82 activate
  neighbor 2600:a801:830:1::83 activate
  neighbor 2600:a801:830:1::1 activate
 exit-address-family

 address-family ipv4 unicast
  network 10.0.0.81/32
  network 10.0.81.0/24
  neighbor 192.168.1.82 activate
  neighbor 192.168.1.83 activate
  neighbor 192.168.1.1 activate
 exit-address-family
``` 
 </details>
