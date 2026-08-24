---
title: "Introduction"
source_gist: https://gist.github.com/scyto/042c8c41b23bd5ddb31d1e4e38156dff
---

# Introduction

This one is the one that has to work, even more so the domain controllers.
[This is what my swarm looks like](../../docker-swarm/index.md)

you may want to read from the bottom up as later migrations are where i had the process more locked and less experimentation

## The plan
So the plan is as follows (and is based on my experience with home assistant oddlye enough)
1. Backup node 1 VM with synology hyper-v backup
2. use `systemctl stop docker` then `systemctl disable docker` then `systemctl stop glusterd` then `systemctl disable glusterd` this is beecause i don't want these to start until i am 100% sure the VM is up, stable and with the right IP address etc 
3. shutdown the node on hyper-v and set start policy to 'nothing' - i can't risk this coming back up mid migration!
4. Migrate the OS disk and gluster disk from docker node 1 on hyper-v
5. create VM in proxmox with:
    1. uefi bios
    2. tpm disk
    3. uefi disks with keys not enrolled (this is critical)
    4. with virtio networking bound to a dead bridge so it cannot talk to network on first boot (until i have chance to hard set IP etc)
6. import both disks with `qm disk import <vmID> <diskname> <target volume>`
7. once imported reattach disks process:
    1. attach each disk as virtio block with write through and discard enabled
    2. change boot option to a)enable boot from the new OS disk b) disable all other bootable items
8. boot, setip address etc
9. reboot to make sure networking connectivity is ok
10. retart and re-enable gluster service - check running, check consistency etc 
11. if good restart and re-enable the docker service

## What happened in the real world...

### Docker03
backing up now... all ok

- stopping and diabling docker - also need to stop and disable `docker.socket` in addtion to `docker` and make sure it is all stoped along with stopping gluster (stop docker first then gluster)
- stopped gluster ok
- exported disks ok
- importing - Docker03.vhdx will be first disk imported, gluster.vhdx will be second disk imported
- both disks seem to have imprted ok 
- hmm won't boot, need to investigate

To boot [follow these steps](docker-swarm-vms-efi-bios.md)

- yes those steps got me booted
- on login i used `sudo fdisk -1` to look at partitions 0 interestingly all my disks are now listed as /dev/vdXX instead of /dev/sdXX - i need to think aboout this.

Ok so the only disk i care about here is the gluster disk (/dev/vdb1)  it seems that in the fstab i was wise and followed guidnace to use UUID not absolute path, this means while the dev name has changed the mount command should still work just fine... unless i am missing something...

<img width="637" alt="image" src="../../../assets/img/c769f4157d63.png">

so great enws, gluster came up fine when i re-enabled it, no errrors shown by various gluster peer and gluster volume commands.
however the local mount seemed to not have worked correctly, not sure why, findmnt is no use to troublehsoot due to bugs with how it scans glusterfs (fixed in more recent version).

i re-enabled and started docker and docker.socket

tl;dr eveything seems great

I will give this a couple of days, then start moving nodes 1 and 2 over..

<img width="800" alt="image" src="../../../assets/img/b8cf6baf5665.png">

### Docker02

#### Prep, Backup & Export
1. `apt install qemu-guest-agent` on docker vm host 
2. stop docker, then docker.socket - then disable in the same order (doing it in the opposite order causes hangs that are scary)
3. checked all swarm services migrated to docker01 vm (still on hyper-v) or docker03 vm (on proxmox) - make sure there are no bouncing services and all is stable
4. stop and dsiable gluster on docker02
6. backup VM 
7. shutdown VM
8. export VM to folder that is shared on hyper-v and mounted in proxmox
9. create VM on promox node 2 (remember don't pre-enroll EFI keys)
 
<img width="500" alt="image" src="../../../assets/img/84105ccb5611.png">

#### Import and VM creation and boot
1. import both disks with `qm disk import <vmID> <diskname> <target volume>`  the path for diskname will be the mounted folder

<img width="500" alt="image" src="../../../assets/img/0a81906666cc.png">

2. attach disks as virtio scsi (not block as that causes me weird issues with gluster and mounts - YMMV)

<img width="500" alt="image" src="../../../assets/img/f8579c54d551.png">

3. enable boot  options for the added boot drive (if you don't do this VM will not boot).

<img width="300" alt="image" src="../../../assets/img/8747b58b19d0.png">

4. boot and enter bios to change [as per this gist](docker-swarm-vms-efi-bios.md).
5. you should now be booted into your machine

#### Fixup (check netork, disks, etc)

The networking adapater on my install changes from eth0 to a 'predictable' interface name like enp6s18.  I could reconfigure my network interfaces file to reflect this change AND any software that was uing eth0 but I also have macvlans configured in my swarm using eth0 as parent interface, to avoid reconfiguring those i renamed the interface back to eth0 as follows

1. issue `nano /etc/systemd/network/10-rename-to-eth0.link`

With the following content in the file(note the MAC address should be the one you see in proxmox for this VM)

```
[Match]
MACAddress=DE:9F:76:12:63:23
[Link]
Name=eth0
```
save the file

One could also do this by disabling predictable naming with grub, but this will be less predictable if you are messing with adding others interfaces etc.

2. use fdisk to make sure all you drives are how you expect (note so long as used UUID in fstab you should not have to worry about changing anything).

<img width="200" alt="image" src="../../../assets/img/2a5cd928cbab.png">

3. reboot - yes i know one should be able to just run sysctl for this, but call me old fashioned
4. re-enable glusterd with `systemctl enable glusterd` and `systemctl start glusterd`
5. check gluster health with `gluster peer status` and `gluster pool list` and `gluster volume status` if all looks ok then proceed (it did look ok first time! )
6. reeneable docker service  with `systemctl enable docker` and `systemctl enable docker.socket`
7. start docker service with `systemctl start docker` and `systemctl start docker.socket`

Now check that the swarm has running services etc and keep an eye on it for a day or so before doing last node (docker01) one IMO

### Docker 01.

Before doing anything else in the swarm issue a `sudo docker node update --availability drain Docker01` and check all your services start on your other nodes.  This is how you can be sure your swarm is ok and ready for you to start messing.  Oh also you might want to make all nodes managers....  i learn't these two the hardware doing docker02 and docker03 where i nearly lost my swarm because it turned out docker02 and docker03 were not quite as healthy as i thought - doing the command above would have proved that before i did anything.  Good news, i lost nothing and a reboot of node 1 actually fixed the issue.  This was nothing to do with promox or migration of VMs.

Anyhoo

after doing `sudo docker node update --availability drain Docker01` do `sudo docker service ls` your services should show them being full rpelicated like this:

```
user@Docker01:~$ sudo docker service ls 
ID             NAME                              MODE         REPLICAS   IMAGE                                             PORTS
zmgmprmvt1bc   adguard_adguard1                  replicated   1/1        adguard/adguardhome:latest                        
ajbqs3okwao7   adguard_adguard2                  replicated   1/1        adguard/adguardhome:latest                        
vm2zwm4b1rb5   adguard_adguardhome-sync          replicated   1/1        ghcr.io/bakito/adguardhome-sync:latest            
mhv0e91y1eyj   agent_agent                       global       2/2        portainer/agent:latest                            
q0o11y7lzu0z   apprise_apprise-api               replicated   1/1        lscr.io/linuxserver/apprise-api:latest            *:8050->8000/tcp
t2b4h5t40ndi   autolabel_dockerautolabel         replicated   1/1        davideshay/dockerautolabel:latest                 
y1y1g4stoakr   cloudflare-ddns_cloudflare-ddns   replicated   1/1        oznu/cloudflare-ddns:latest                       
mmqxwvg0y1wn   cluodflared_portainer-tunnel      replicated   1/1        cloudflare/cloudflared:2022.7.1                   
pbthkozio6wb   dockerproxy_dockerproxy           global       2/2        ghcr.io/tecnativa/docker-socket-proxy:latest      *:2375->2375/tcp
cegzyr148wm0   infinitude_infinitude             replicated   1/1        nebulous/infinitude:latest                        *:4000->3000/tcp
5oi1lneq2rk9   mqtt_mosquitto                    replicated   1/1        eclipse-mosquitto:latest                          *:1883->1883/tcp, *:9005->9001/tcp
q18jjgt1n8nh   npm_app                           replicated   1/1        jc21/nginx-proxy-manager:latest                   *:180-181->80-81/tcp, *:1443->443/tcp
reszh56oksy7   npm_db                            replicated   1/1        jc21/mariadb-aria:latest                          
i71f0bv6omlh   oauth_oauth2-proxy                replicated   1/1        quay.io/oauth2-proxy/oauth2-proxy:latest          *:4180->4180/tcp
t7nwstj8x3am   portainer_portainer               replicated   1/1        portainer/portainer-ee:latest                     *:8000->8000/tcp, *:9000->9000/tcp, *:9443->9443/tcp
qj0zbbezgz0g   shepherd_shepherd                 replicated   1/1        mazzolino/shepherd:latest                         
zx55uwcrs7yq   swag_swag                         replicated   1/1        ghcr.io/linuxserver/swag:latest                   *:8056->80/tcp, *:44356->443/tcp
d1pmnxgs0d6k   unifiapibrowser_unifiapibrowser   replicated   1/1        scyto/unifibrowser:latest                         *:8010->8000/tcp
94lk9rdibkxn   watchtower_watchtower             global       2/2        containrrr/watchtower:latest                      
1cn9mhszh4ak   wordpress_db                      replicated   1/1        mysql:5.7                                         
f04v1qnunbe4   wordpress_wordpress               replicated   1/1        wordpress:latest                                  *:8080->80/tcp, *:9090->9000/tcp
62kp1w2k2p15   zabbix_zabbix-db                  replicated   1/1        mariadb:10.11.4                                   
6lsg98k3595e   zabbix_zabbix-server              replicated   1/1        zabbix/zabbix-server-mysql:ubuntu-6.4-latest      *:10051->10051/tcp
qdkljk7j96ry   zabbix_zabbix-web                 replicated   1/1        zabbix/zabbix-web-nginx-mysql:ubuntu-6.4-latest   *:10052->8080/tcp
```
and issuing a `sudo docker container ls` on this node should show:

```
user@Docker01:~$ sudo docker container ls
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
user@Docker01:~$ 
```

If so now you are good to use the same basic steps we used for node 2 and 3:

1. install quest tools  `apt install qemu-guest-agent`
2. stop and disable docker on node `systemctl stop docker` and `systemctl stop docker.socket` then `systemctl disable docker` and `systemctl disable docker.socket` 
3. stop and disable glusterd on node  `systemctl stop glusterd` then `systemctl disable glusterd` 
4. backup node
5. shutodwn VM in hyper-v and confgure start policy to nothing
6. export VHD from hyper-v to CIFS location
7. import VHD to promxox from CIFS location - `qm disk import 111  Docker01.vhdx local-lvm` and `qm disk import 111  gluster.vhdx local-lvm`
8. configure VM, attach disks, define boot order
9. start vm, interrup boot with `esc`and [add needed EFI entry](docker-swarm-vms-efi-bios.md)
10. boot to os
11. add rename logic for network card...

issue `nano /etc/systemd/network/10-rename-to-eth0.link`

With the following content in the file(note the MAC address should be the one you see in proxmox for this VM)

```
[Match]
MACAddress=DE:9F:76:12:63:23
[Link]
Name=eth0
```
save the file, reboot

13. enable and start gluster - make sure the gluster volume is absolutely ok before starting docker `gluster pool list` and `gluster volume status` and `gluster perr status`
14. enable and start docker - let nodes rebalance over time, keep an eye on it. `systemctl enable docker`, `systemctl enable docker.socket`, `systemctl start docker` & `systemctl start docker.socket` 

You are done.
