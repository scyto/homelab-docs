---
title: "Proxmox cluster Setup"
source_gist: https://gist.github.com/scyto/645193291b9a81eb3cb6ebefe68274ae
---

# Proxmox cluster Setup
[this gist is part of this series](index.md)

## Network Design
Put simply I am not sure what the design should be. I have the thunderbolt mesh network and the 2.5gbe NIC on each node.  The ideal design guidelies cause my brain to have a race conditions because:

1. ceph shold have a dedicated network
2. proxmox should not have migration traffic and cluster communications network
3. one wants cluster communicationsnetwork reddundant

I have 3 networks:
1. Onboard 2.5gb NIC connected to one switch for subnet IPv4 `192.168.1.0/24` and IPv6 /64 address (my LAN)
2. Thunderbolt mesh connected in a ring for subnet fc00::80/124
    - this has 3 single address subnets `fc00::81/128`, `fc00::82/128` and `fc00::83/128` these are used for FRR Openfabric  routing between nodes
3. Addtional 2.5Gbe using (NUCIOALUWS) add-on afor subnet TBD

    - cluster (aka corosync) network uses network 1 (2.5gbe)
    - ceph migration traffic uses network 2 (thunderbolt)
    - ceph public network uses network 2 (thunderbolt
    - CT and VM migration traffic uses network 2 (thunderbolt network)

I have not yet decided what network 3 will be used for, options are:

   - cluster public network that other devices use to access the cluster or its resources
   - backup corosync (though i don't see a reason not to have corosync on all 3 networks)
   - ceph public network - but I assume this is what the VMs uses so it makes sense to i want that on the 26Gbps thunderbolt mesh too


## Create Cluster
You should have 3 browser tabs open for this, one for each node's management IP. 

### setup on node 1

1. navigate to `Datacenter > Cluster` and click `Create Cluster`
2. name the cluster e.g. `pve-cluster1`
3. set link 0 to the IPv4 address (in my case `192.168.1.81` on interface vmbr0)
4. click `create`

### Join node 2 
1. on node 2 in `Datacenter >  Cluster` click `join information`
2. the IP address should be node 1 IPv4 address
3. click `copy information`
4. open tab 2 in your browser to node 2 management page
5. navingate to `Datacenter > Cluster` and click join cluster
7. paste the information into the dialog box that you collected in step 3
8. Fill the root password in of node 1
9. Select Link 0 as `192.168.1.82` 
10. click button `join 'pve-cluster1'`

### Join node 3 
1. on node 1 in `Datacenter > Cluster` click `join information`
2. the IP address should be node 1 IPv4 address
3. click `copy information`
4. open tab 2 in your browser to node 3 management page
5. navingate to `Datacenter > Cluster` and click join cluster
7. paste the information into the dialog box that you collected in step 3
8. Fill the root password in of node 1
9. Select Link 0 as `192.168.1.83` 
10. click button `join 'pve-cluster1'`

at this point close your pv2 and pve 3 tabs - you can now manage all 3 cluster nodes from node 1 (or any node)

## Define Migration Network

1. navigate in webui to `Datacenter > Options`
2. double click `Migration Settings`
3. select  any networkand click ok - this is just to create an entry in the config file 
4. edit with `nano /etc/pve/datacenter.cfg` and change: 
  `migration: network=10.0.0.81/32,type=secure`
  to
  `migration: network=fc00::80/124,type=insecure`
This is because a)this subnet contains `fc00::80` thru `fc00::8f`; and b) because it is 100% isolated network it can be insecure give a small speed boost 

## Configuring for High Availability

1. navigate in webui to `Datacenter > HA > Groups`
2. click create
3. Name the cluster (ID) `ClusterGroup1`
4. add all 3 nodes and then click `create`
