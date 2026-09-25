---
title: "Mounting CephFS on a LAN client"
source_gist: https://gist.github.com/scyto/61b38c47cb2c79db279ee1cbb6f31772
---

# mounting cephFS on a LAN client

how a machine that is not a Proxmox node mounts a cephFS filesystem with the
kernel client: a VM, another linux box, a pi. my docker VMs do not do this any
more, they get cephFS through [virtiofs](../cephfs-virtiofs-passthrough.md). this
is for anything else on the LAN that needs the cluster.

the examples mount the filesystem `docker` on a client called `lan01`. checked
against the Ceph docs and Proxmox VE's own source, and tested read only against
Ceph 20.2 from a Debian 12 VM (kernel 6.1, `ceph-common` 16.2).

## what the client needs

- **a route to the mesh**, to the monitors, the MDS **and every OSD**. the kernel
  client reads and writes file data on the OSDs itself, so reaching only the
  monitors is not enough. [LAN access to the mesh](lan-access-to-mesh.md) is how
  mine get there
- **`ceph-common`**, for the mount helper
- **`/etc/ceph/ceph.conf`**, a minimal config so it can find the monitors
- **`/etc/ceph/ceph.client.lan01.keyring`**, its own Ceph user

## 1. a user for the client

on any Proxmox node. one user per client, never a shared one and never
`client.admin`, so taking one client away is one command and a lost key only
opens what that client could reach.

```
umask 077
ceph fs ls
ceph fs authorize docker client.lan01 / rw > /root/ceph.client.lan01.keyring
ceph config generate-minimal-conf > /root/ceph.conf
ceph auth get client.lan01 | grep caps
```

- `umask 077` makes both files readable by root only. `scp` keeps a file's mode,
  and without this the keyring lands in the client's home directory readable by
  every user on it
- `ceph fs ls` lists the filesystem names. `docker` is mine
- `ceph fs authorize` works out the capabilities itself, including the data
  pools, so there are no pool names to get wrong. it prints the keyring, which is
  the key, so it goes to a file, not the screen
- `/ rw` is the path and the access. `/ r` is read only. `/backups rw` gives one
  directory, and the client can then only mount that directory. `rwp` also
  allows layouts and quotas, `rws` snapshots. `root_squash` after the access
  stops root on the client changing anything
- the last line shows the caps it made. for `/ rw` on Ceph 20.2:

    ```
    caps mds = "allow rw fsname=docker"
    caps mon = "allow r fsname=docker"
    caps osd = "allow rw tag cephfs data=docker"
    ```

    a read only user gets `allow r` on the `mds` and `osd` lines

**not in `/etc/pve/priv/ceph/`.** Proxmox reads `<storage id>.secret`,
`<storage id>.keyring` and `<storage id>.conf` from there for its own Ceph and
cephFS storages. a client's file that happens to have a storage's name replaces
that storage's credentials, and the storage stops mounting the next time it
mounts.

## 2. copy the files to the client

from your own machine, which can reach both. the client never gets SSH to a
Proxmox node:

```
scp -3 root@pve1:/root/ceph.client.lan01.keyring root@pve1:/root/ceph.conf alex@lan01:
ssh root@pve1 rm /root/ceph.client.lan01.keyring /root/ceph.conf
```

`-3` sends the copy through your machine rather than from one host to the other.

on the client, as the user the files were copied to. in a root shell `~` is
`/root` and the files are not there:

```
sudo apt install ceph-common
ls -l /etc/ceph/
sudo install -d -m 755 /etc/ceph
sudo install -m 644 -o root -g root ~/ceph.conf /etc/ceph/ceph.conf
sudo install -m 600 -o root -g root ~/ceph.client.lan01.keyring /etc/ceph/ceph.client.lan01.keyring
rm ~/ceph.conf ~/ceph.client.lan01.keyring
```

look at the `ls` before installing. an existing `ceph.conf` may belong to
something else, move it aside rather than overwrite it.

## 3. mount it

```
sudo mkdir -p /mnt/cephfs
sudo mount -t ceph :/ /mnt/cephfs -o name=lan01,fs=docker
```

- `name=lan01` is the user without `client.`, `fs=docker` the filesystem, and
  `:/` the path inside it, which has to be within what step 1 allowed. the monitors
  come from `ceph.conf`, which is what the empty part before the `:` means
- the helper reads the key from `/etc/ceph/ceph.client.lan01.keyring`, so it never
  goes on the command line
- for a read only user add `ro`: `-o name=lan01,fs=docker,ro`
- `findmnt -t ceph` afterwards shows `mds_namespace=docker`. the kernel's older
  name for `fs=`

**the newer form**, `sudo mount -t ceph lan01@.docker=/ /mnt/cephfs`, is what the
Ceph docs show now. the mount helper in Debian 12's `ceph-common` 16.2 does not
understand it and fails with:

```
source mount path was not specified
unable to parse mount source: -22
```

the form above worked there. i have not tried the newer form with a newer helper.

then check it can read **file contents**, as well as list them. a listing only
needs the MDS. contents need the OSDs, so a missing route to an OSD, or caps that
name the wrong pools, only shows up here:

```
ls /mnt/cephfs
f=$(sudo find /mnt/cephfs -maxdepth 2 -type f -size +0 -print -quit); echo "$f"
sudo head -c 1 "$f" > /dev/null && echo contents ok
```

for a read write client, check it can **write** as well. reading proves nothing
about that: a mount that came up read only, or caps without write, still prints
`contents ok`. an empty file only touches the MDS, so this writes a block and
forces it out to the OSDs before removing it:

```
t=$(sudo mktemp -p /mnt/cephfs .write-test.XXXXXX) && sudo dd if=/dev/zero of="$t" bs=4k count=1 conv=fsync status=none && sudo rm "$t" && echo writes ok
```

on a read only mount it stops at `mktemp` with `Read-only file system` and
writes nothing. with `root_squash`, root cannot write, so run it as a user who can,
without `sudo`.

## 4. mount at boot

`/etc/fstab`:

```
:/ /mnt/cephfs ceph name=lan01,fs=docker,noatime,_netdev 0 0
```

- `_netdev` makes it wait for the network
- `0 0` because there is nothing for fsck to check on a network filesystem

check the line before a reboot finds a mistake for you:

```
sudo findmnt --verify --verbose
sudo umount /mnt/cephfs
sudo mount /mnt/cephfs
```

`findmnt` warns `unreachable source: :/` and `cannot detect on-disk filesystem
type` for this line. both are expected, there is no local device to check. what
matters is `0 parse errors, 0 errors`, and that the `mount` works.

## removing a client

unmount it on the client, then on a Proxmox node:

```
ceph auth rm client.lan01
```

and delete its keyring and fstab line on the client.

## files

| where | file | mode | holds |
| --- | --- | --- | --- |
| client | `/etc/ceph/ceph.conf` | 644 | the cluster's fsid and monitor addresses, no keys |
| client | `/etc/ceph/ceph.client.lan01.keyring` | 600 | this client's key |
| Proxmox node | nothing kept | | the copies in `/root` are deleted in step 2 |
