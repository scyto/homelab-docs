---
title: "How to get working in a privileged container"
source_gist: https://gist.github.com/scyto/e4e3de35ee23fdb4ae5d5a3b85c16ed3
---

# How to get working in a privileged container
wow this one is hard.... you can avoid the id mapping stuff by not using a privileged container...

## Assumptions:
1. you have a debian 12 container, you added the non-free deb and have installed the non-free drivers as per the host instructions
2. you have run `cat /etc/groups` in the container and noted down the GID for render (lets call that CTRGID) and gid for video (lets call that CTVGID).
4. you have run `cat /etc/groups` in the container and noted down the GID for render (lets call that HSTRGID) and gid for video (lets call that HSTVGID).
5 that you have va info fully working

## Create Container
1. create container privileged, with debian 12, starts it
2. apt update, apt upgrade, install non free drivers, vainfo and intel_gpu_top tools
3. add root to user and video groups (this will mean when we get to ID mapping you don't need to tart about with user mappings - only group ones)

```
usermod -a -G render root
usermod -a -G video root
```
4. shutdown container

## Edit container conf file
1. These are stored in /etc/pve/lxc and have the VMID.conf anme
2. `nano /etc/pve/lxc/VMID.conf`

### Add lxc device mapping

Here you add a line for the card uyou want and the rendere.
Note if you map a VF (card) to a container it means that is hard mapped, if you have that VF in a pool for VMs please remove it from the pool (this means also these containers cannot be HA)

In the example below i chose card6 - which is renderD134
These are mapped into the container as card0 and renderD128
Change your numbers as per your own VF / card mappings

```
lxc.cgroup2.devices.allow: c 226:6 rwm
lxc.mount.entry: /dev/dri/card6 dev/dri/card0 none bind,optional,create=file

lxc.cgroup2.devices.allow: c 226:134 rwm
lxc.mount.entry: /dev/dri/renderD134 dev/dri/renderD128 none bind,optional,create=file

```



### Add ID mapping (only needed in unprivileged)
1. add the following... and here it gets complex as it will vary based on the numbers you recorded earlier - let me try... the aim is to have a continguois block of mappings but the syntax is um difficult...

```
lxc.idmap: u 0 100000 65536
lxc.idmap: g 0 100000 CTVGID
lxc.idmap: g CTVGID HSTVGID 1
lxc.idmap: g CTVGID+1 1000{CTVGID+1} CTRGID-CTVGID-1
lxc.idmap: g CTRGID HSTVGID 1
lxc.idmap: g CTRGID+1 100{CTRGID+1} 65536-{CTRGID+1}
```

so as an example, these are my values:

```
        host > ct
video:    44 > 44
render:  104 > 106
```

this is what i added to my VMID.conf file (in  my case /etc/pve/lxc/107.conf
```
lxc.idmap: u 0 100000 65536
lxc.idmap: g 0 100000 44
lxc.idmap: g 44 44 1
lxc.idmap: g 45 100045 61
lxc.idmap: g 106 104 1
lxc.idmap: g 107 100107 65429
```

4. add your two CT values to `nano /etc/subgid`  (only needed in unprivileged)

in my case:
```
root:106:1
root:44:1
```

after this you should be able to start up the container and run vainfo and perform transcoding. 

check permissions with `ls -la /dev/dri` it should look like this:
```
root@vGPU-debian-test:~# ls -la /dev/dri
total 0
drwxr-xr-x 2 root   root         80 Oct  7 00:22 .
drwxr-xr-x 7 root   root        500 Oct  7 00:22 ..
crw-rw-rw- 1 nobody video  226,   0 Oct  4 21:42 card0
crw-rw-rw- 1 nobody render 226, 128 Oct  4 21:42 renderD128
```
if the group names do not say video and render then you did something wrong


**Note: YYMV **

For example plex HW transcoded just fine on my system. 

Emby on the otherhand seems to interrogate the kernel driver directly and gets the wrong answers - this is IMHO an issue with their detection logic not supporting this scenario.

Another example is intel_gpu_top which doesn't seem to work in this mode either - this is because it only works with the PMUs not the VFs (so somoene said)

Or maybe i just have no clue what i am doing, lol.

---work in progress 2023.10.6---
