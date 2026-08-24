---
title: "Proxmox Backup"
source_gist: https://gist.github.com/scyto/61dcfff1d0128d9df85cf57b756c599c
---

# Proxmox Backup
At this time proxmox backup only backs up VM and Containers - ths guide covers that.

What i didn't realize is the backup job is still defined on the cluster and PBS provides a new storage type that dedupes and managed all the vzdump files created - which is cool. 

I decided to run proxmox backup on my Synology NAS where it has more reliable connection to the NAS (i.e. via memory) for doing deduple, garbage collection, prune, verification etc.  However the steps here generally remain true.

Once again i used one of [Derek Seaman's Awesome Blogs](https://www.derekseaman.com/2023/04/how-to-setup-synology-nfs-for-proxmox-backup-server-datastore.html) for the basis of this - but with my own tweaks (like using SMB instead of CIFS. As of 9/21 my tweaks are signifcnant, in the original blog it is missing steps to enable encoding acceleration in CTs and VMs.

[this gist is part of this series](../index.md)

## Setup Proxmox Backup
1. create a PBS VM on your synology (see Derek's blog if you don't know how to do that)
2. set password, IP, etc, call it something like pbs.mydomain.com etc
3. login and check it looks ok - it should be!

## Prepare The Synology (abbreviated edition)
1. create a synology shared folder called proxmox
    - hide it from explorer
    - don't enable compression
    - don't enable encryption unless you are truly paranoid
    - assign only admins to it
2. create a new user called proxmox on the synology for promox backup to access the shared folder 
    - set password to expire
    - assign them to only the users group
    - give them permissions to no apps and only the proxmox share created earlier

## Configure Mount on PBS
1. login to PBS and access the shell
2. create a username and password file using `nano /etc/samba/.syn01` in this example syn01 is the name of my synology
3. add the following based on the user you made ealier
```
username=proxmox
password=<yourpassword>
domain=WORKGROUP
```
4. save the file
5. create a mount point `mkdir /mnt/syn01`
6. now add a mount to fstab with the following command
```
echo "//192.168.1.30/proxmox /mnt/syn01 cifs rw,auto,uid=34,noforceuid,gid=34,noforcegid,credentials=/etc/samba/.syn01 0 0" >> /etc/fstab

note: in this example use your synology IP not the example above, if you did my other instructions correctly that is all you should need to change.

The uid and gid ensure you have no strnage issues with permission - these map to the backup user and group in proxmox

```
7. perform a `systemctl daemon-reload` without this the fstab changed won't be picked up
8. now mount the share with `umount -a`
9. create a test fie with `nano /mnt/syn01/test.txt` populate it with some text and save - you should see it appear on the synology in file explorer with no errors

## Add stroage in proxmox backup
1. navigae to `Datastores` and click `add datastore`
2. name - call it whatevr you want, say `syn01`
3. backing path is `/mnt/syn01` leave GC and prune settings as is
4. click add

At this point it will add the storage and create all the chunks, this may take a few minutes.
Aftewhich you should have a working datastore

## Configure Certificates
If you plan to use SSL certificates you should configure them at this point as configuring later will invalidate the fingerprint. so if you do it after the nex step remember you will get a 500 error and need to copy the new fingerprint.

## Add storage to PVE cluster
1. on pve cluster navigate to `Datacenter storage`
2. click `add` and select `prxmox backup server`
3. ID is whatever name you want to call it, say, `pbs`
4. server = ip address or fqdn of your pbs server
5. username and password is the *pbs* username and password you set earlier
6. datastore is what you ever  you named it ealier - in this example `syn01` 
7. fingerpint - to get the fingeprint on the pbs server click `dasboard` click `show figerprint` click `copy`
8. now on the pve cluster console paste in the fingerprint and click `add`
9. (the namespace of Root can be left as-is)

You can now set your backup, gc, prune and verify jobs etc - this is beyond the cope of this gist
