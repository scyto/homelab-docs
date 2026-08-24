---
title: "Install & Configure GlusterFS"
source_gist: https://gist.github.com/scyto/452fc778c4c3ba7caf03b833151e84a1
---

# Install & Configure GlusterFS

Assumes you installed debian, docker, etc as [per the list here](index.md)

## Assumptions
- I will have one gluster volume i will call `glusterfs-vol1`
- I will install glusterfs on my docker nodes (best practice is to have seperate dedicated VMs)
- I have 3 nodes in my cluster  (docker01, docker02, docker03)
- I will have one brick per node (brick1, brick2, brick3)
- the volume will be dispered - [more on volume types](https://docs.gluster.org/en/latest/Quick-Start-Guide/Architecture/#types-of-volumes)

## Prepare Disks
### Prepare disks on hypervisor
Add a VHD to each of your docker host VMs - for example a 100GB Volume
If using Hyper-V this can be done without rebooting (add it as new SCSI VHD and the VM OS will detect it instantly)

### Partition, format and mount the underlying storage (be careful)
Perform these steps on every node.

`sudo lsblk` to confirm device node (should be sdb but could be different if you diverged from any of gists)

`sudo fdisk /dev/sdb`    (then `g`, then `n` and accept defaults and lastly `w` to write out changes)

`sudo mkfs.xfs /dev/sdb1` (this formats the new paritions with XFS)

`sudo mkdir /mnt/glusterfs` (this is where you will mount the new parition)

`sudo mount /dev/sdb1 /mnt/glusterfs` (this mounts and is used in next steps, don't miss).


### on docker01 
`sudo mkdir /mnt/glusterfs/vol1-brick1` this created the folder where brick1 will be stored

`sudo ls -al /dev/disk/by-uuid/` this gets you the UUID for the partition you created earlier

edit fstab (be careful) with `sudo nano /etc/fstab`
add the followling line as the last line in fstab, use the UUID you got in the last step, do not use the one here. 
`UUID=c78ed594-ef62-445d-9486-10938f49b603 /mnt/glusterfs xfs  defaults  0  0`

`sudo findmnt --verify` you should see no errors related to /dev/sdb or /dev/sb1 (you may see errors about CD-ROM those can be ignored)  if you get ANY errors do not proceed until you have checked your previous work

### on docker02 
`sudo mkdir /mnt/glusterfs/vol1-brick2` this created the folder where brick2 will be stored

`sudo ls -al /dev/disk/by-uuid/` this gets you the UUID for the partition you created earlier

edit fstab (be careful) with `sudo nano /etc/fstab`
add the followling line as the last line in fstab, use the UUID you got in the last step, do not use the one here.
`UUID=c78ed594-ef62-445d-9486-10938f49b603 /mnt/glusterfs xfs  defaults  0  0`

`sudo findmnt --verify` you should see no errors related to /dev/sdb or /dev/sb1 (you may see errors about CD-ROM those can be ignored)  if you get ANY errors do not proceed until you have checked your previous work

### on docker03 
`sudo mkdir /mnt/glusterfs/vol1-brick3` this created the folder where brick3 will be stored

`sudo ls -al /dev/disk/by-uuid/` this gets you the UUID for the partition you created earlier

edit fstab (be careful) with `sudo nano /etc/fstab`
add the followling line as the last line in fstab, use the UUID you got in the last step, do not use the one here.
`UUID=c78ed594-ef62-445d-9486-10938f49b603 /mnt/glusterfs xfs  defaults  0  0`

`sudo findmnt --verify` you should see no errors related to /dev/sdb or /dev/sdb1 (you may see errors about CD-ROM those can be ignored)  if you get ANY errors do not proceed until you have checked your previous work

## Install & Configure GlusterFS

### On all nodes:
```
sudo apt-get install glusterfs-server
sudo systemctl start glusterd
sudo systemctl enable glusterd
```

## Create the glusterfs volume
### On the master node (docker01) - note you must run sudo -s and not sudo for each command
```
sudo -s
gluster peer probe docker02.alexbal.com; gluster peer probe docker03.alexbal.com;
gluster pool list
gluster volume create gluster-vol1 disperse 3 redundancy 1 docker01.yourdomain.com:/mnt/glusterfs/vol1-brick1 docker02.yourdomain.com:/mnt/glusterfs/vol1-brick2 docker03.yourdomain.com:/mnt/glusterfs/vol1-brick3
gluster volume start gluster-vol1
gluster volume info  gluster-vol1
 ```

### on all docker hosts
`sudo mkdir /mnt/gluster-vol1` make the mount point

`sudo nano /etc/fstab` edit the fstab

add the following as the last line in the fstab
`localhost:/gluster-vol1  /mnt/gluster-vol1 glusterfs  defaults,_netdev,noauto,x-systemd.automount        0 0`
exit and save 

`sudo mount -a` should mount with no errors

`sudo df /mnt/gluster-vol1/` should return details about the gluster file system (size etc)


To test create a file using touch `sudo touch /mnt/gluster-vol1/hello-world-txt` now check for that file in the same path on the other 2 nodes.  If you did everything correctly you now have a replicating and redundant file system!


Note: `findmnt --verify` cant be used for this mount as it doesn't support checking glusterfs
