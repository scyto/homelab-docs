---
title: "Configuring CephFS to store ISOs for VMs and Templates for Containers"
source_gist: https://gist.github.com/scyto/941b24efd1ac0bf9b3cd30c3fb1e5341
---

# Configuring CephFS to store ISOs for VMs and Templates for Containers
This gist assume you have setup Ceph as per earlier gist in this sequence

I found it annoying to upload ISO to each node in the cluster, download CT templates to each node.  
I thought setting up cedph for these would be a great idea (and it is). 

[this gist is part of this series](index.md)

## create cephfs pools
1. In the gui navigate to `Datcenter > node name > ceph`
2. Click `cephfs` node 
3. In Metadata Server area click `create` and create a meta data server on all 3 pve nodes
4. Next click Create CephFS and give it a name like `ISOs-Templates`
5. Ensure `add as storage` is CHECKED
6. click `create`

## set storage use 
2. Click `Datacenter > storage`
3. Select `ISOs-Templates`
4. 5. Edit the content section to remove VZDump Backup file and snippets
6. edit backup settings as you prefer and click `ok`

<p align="center">
<img width="577" alt="image" src="../../assets/img/7918a644aa52.png">
</p>

## add ISOs or CT templates
1. on any node navigate to ISOs-Temples disk in the left pane and select it
2. now select ISO images in right pane and click `upload`
3. upload an ISO
4. now select CT Templates
5. click `template`
6. choose `debian-12-standard` and click download

## check it worked
1. now click on ISOs-Templates disk on any other node and you will see the file is visible on all nodes
2. do same for VT Templates
