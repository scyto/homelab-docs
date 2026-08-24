---
title: "weird stuff troublehsooting etc"
source_gist: https://gist.github.com/scyto/f04f27ecc07b1dc0662a5fdc38a4418c
---

# weird stuff troublehsooting etc

[this gist is part of this series](index.md)

### PROXMOX Setup Weirdness Observed	
1. Most of the time gui setup didn't get dhcp address from my server, one time in 6 installs it did.  	
2. Sometimes gui setup populated an example IPv4 address, sometimes an actual IPv6 address and one time real DCHP IPv4 address	
3. on one node in 6 installs it added a thunderbol0 entry to /etc/network/interaces resulting in what you see below, the fix was to remove from interfaces file	
<img width="1046" alt="image" src="../../assets/img/79f9ae9ac014.png">	

 4. sometimes after setup the tunderbolt modules load and sometimes they don't - i don't know why, i currently have 1 machine with them specified in /etc/modules file and 2 machines without - i figured out this is (stupidly) by design, one machine in the cluster needs to manually have the the modules loaded (but this will cause other machines to load them on the fly) as such its best to define them on all nodes.	

 5. on node 3 i accidentally gave it an IP of 192.168.1.183 instead of 192.168.1.83 during gui install.  after install i changed this IIRC in /etc/network/interfaces and all seemed ok, but when i tried to join the cluster it failed saying 192.168.1.183 didn't exist on the local machine.  The fix was to edit /etc/hosts which had the incorrect IP mapped as follows `192.168.1.183 pve3.mydomain.com pve3` correcting the IP on the line seemed to fix it.	
 6. IPv6 over thunderbolt seem to be quite broken on Proxmox VE8 and Debian 12 - as such this guide switched to all IPv4 but you can find the IPv6 routed mesh page [here](thunderbolt/ospf6d-mesh-legacy.md) if you are interested.
 
 ## CEPH
 In general setup ceph only once you know the mesh network is stable and can survive cable pulls, managed reboots, node failure.
 Doing ceph and cluster networking after they are fully cofigured rendered my cluster nearly unseable (but never irrevecoably - just need to google the forums a ton)
 
 ### UI very fragile to certain ceph configs
 It seems the UI is super fragile to stupid confis and will stop responding - for example if one delets a cephfs storage item and stops all MDS it can hange.  The only fix is to fix ceph at command line.
 
 For CephFS i found this to be super useful to blow away CephFS pools in strange states
 `pveceph fs destroy ISOs-Templates --remove-pools 1 --remove-storages 1` where the ISOs-Templates is the name of the pool without the \_data or \_metadata suffixes
 
 I also found doing this can leave orphnaned directories in /mnt/pve/ which if are the same as a new CephFS folder you want to create will result in a mount error - i have not yet figure out how to remove these as operations on these folders hangs the shell... 
 
 ### Reseting Ceph
 It is possible to tear down ceph, this is the general approach:
 1. remove pools
 2. remove OSDs
 3. remove mons and managers on all but one node
 4. on laast node to pveceph purge

I did find when things were really screwy and the purge failed or mon deletion fails that one might need to delete one or more of the following:

- delete the file for the failed monitor on its node aka `rm /etc/systemd/system/ceph-mon.target.wants/<monitor name>`
- delere the file for the failed monnitor on its node aka `rm /var/lib/ceph/mon/<monitor name>`
 - source: https://forum.proxmox.com/threads/ceph-how-to-delete-dead-monitor.61172/)
- the enries in the ceph.conf for the ghost mon (never delete the last one this way)

### OSD Couldnt be created
My second and third OSD (first on node 2 and first on node 3) couldn't be created with:
```
create OSD on /dev/nvme0n1 (bluestore)
wiping block device /dev/nvme0n1
200+0 records in
200+0 records out
209715200 bytes (210 MB, 200 MiB) copied, 0.0956093 s, 2.2 GB/s
Running command: /bin/ceph-authtool --gen-print-key
Running command: /bin/ceph --cluster ceph --name client.bootstrap-osd --keyring /var/lib/ceph/bootstrap-osd/ceph.keyring -i - osd new 879da4b3-c227-41a8-823f-a2357fb01af7
 stderr: 2023-08-20T08:18:19.776-0700 7ff8c93b06c0 -1 auth: unable to find a keyring on /etc/pve/priv/ceph.client.bootstrap-osd.keyring: (2) No such file or directory
 stderr: 2023-08-20T08:18:19.776-0700 7ff8c93b06c0 -1 AuthRegistry(0x7ff8c4060610) no keyring found at /etc/pve/priv/ceph.client.bootstrap-osd.keyring, disabling cephx
 stderr: 2023-08-20T08:18:19.780-0700 7ff8c27fc6c0 -1 monclient(hunting): handle_auth_bad_method server allowed_methods [2] but i only support [2]
 stderr: 2023-08-20T08:18:19.780-0700 7ff8c2ffd6c0 -1 monclient(hunting): handle_auth_bad_method server allowed_methods [2] but i only support [2]
 stderr: [errno 13] RADOS permission denied (error connecting to the cluster)
-->  RuntimeError: Unable to create a new OSD id
TASK ERROR: command 'ceph-volume lvm create --cluster-fsid 5e55fd50-d135-413d-bffe-9d0fae0ef5fa --data /dev/nvme0n1' failed: exit code 1
```
fix was to run the following on each node

`ceph auth get client.bootstrap-osd > /var/lib/ceph/bootstrap-osd/ceph.keyring`
source:https://forum.proxmox.com/threads/host-key-verification-failed-when-migrate.41666/

it was unclear to me why this file didn't exist - but i had purged / reinstalled ceph more than a few times - so I suspect that was the issue.


## Migration
My first migration failed with
```
2023-08-20 08:35:44 # /usr/bin/ssh -e none -o 'BatchMode=yes' -o 'HostKeyAlias=pve2' root@192.168.1.82 /bin/true
2023-08-20 08:35:44 Host key verification failed.
2023-08-20 08:35:44 ERROR: migration aborted (duration 00:00:00): Can't connect to destination address using public key
TASK ERROR: migration aborted
```
this was fixed by either one or both of these being done on EVERY node by connecting explictly to the node (not using one node to access another):

```
so maybe this was the magic:
ssh-keygen -f "/etc/ssh/ssh_known_hosts" -R "pve1"
ssh-keygen -f "/etc/ssh/ssh_known_hosts" -R "pve2"
ssh-keygen -f "/etc/ssh/ssh_known_hosts" -R "pve3"

AND / OR
fix migrate ssh issues (hhm why did this work - the names are wrong, maybe it was just clearing down the ssh known hosts files that worked?

ssh -o 'HostKeyAlias=pve1' root@10.0.0.81
exit
ssh -o 'HostKeyAlias=pve2' root@10.0.0.82
exit
ssh -o 'HostKeyAlias=pve3' root@10.0.0.83
exit
``` 
source: https://forum.proxmox.com/threads/host-key-verification-failed-when-migrate.41666/
