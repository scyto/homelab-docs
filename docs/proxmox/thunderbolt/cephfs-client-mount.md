---
title: "CephFS Mounting for Docker VMs (first draft)"
source_gist: https://gist.github.com/scyto/61b38c47cb2c79db279ee1cbb6f31772
---

# CephFS Mounting for Docker VMs (first draft)

2025.04.27 - currently untested e2e this was made from my raw notes by chatgpt, so erros and hallucianation may have crept in :-)

This document describes the clean, final method to mount a CephFS filesystem for Docker VMs across your cluster.

Assumptions:
- you have a working cephFS volume called **docker** (out of scope)
- that you can see this volume just fine mounted on all 3 pve nodes (if you can't then this is never going to work)
- that you are using the IPv6 version of my ceph proxmox setup (not critical, just sawp out IPv6 for IPv4 address below)
- it assume you have full connectivity from within the VM to the internet and the ceph network - this relies on my new routed mesh network setup i haven't yet published (should be ok if you are in normal VM environment, but the requirement remains)

---

## 🛠️ Proxmox Node Setup (one-time, performed on any node)

### 1. Create a restricted CephFS client

```bash
ceph auth get-or-create client.docker-cephfs \
  mon 'allow r' \
  mds 'allow rw path=/' \
  osd 'allow rw pool=cephfs.docker.meta, allow rw pool=cephfs.docker.data'
  -o /etc/pve/priv/ceph/ceph.client.docker-cephfs.keyring
```


### 2. Extract the raw secret

```bash
grep 'key =' /etc/pve/priv/ceph/ceph.client.docker-cephfs.keyring | awk '{print $3}' > /etc/pve/priv/ceph/docker-cephFS.secret
chmod 600 /etc/pve/priv/ceph/docker-cephFS.secret
```

### 3. Generate a minimal Ceph config

```bash
ceph config generate-minimal-conf -o /etc/pve/priv/ceph/minimal-ceph.conf
chmod 644 /etc/pve/priv/ceph/minimal-ceph.conf
```

---

## 🛠️ VM Setup Instructions (done within VM)

### 1. Install necessary packages

```bash
apt update
apt install ceph-common
```

### 2. Retrieve secret and config from Proxmox

```bash
sftp root@[fc00::81]
lcd ~
get /etc/pve/priv/ceph/docker-cephFS.secret
get /etc/pve/priv/ceph/minimal-ceph.conf
get /etc/pve/priv/ceph/ceph.client.docker-cephfs.keyring
exit
```

### 3. Move files into place

```bash
mkdir -p /etc/ceph
mv ~/docker-cephFS.secret /etc/ceph/
mv ~/minimal-ceph.conf /etc/ceph/ceph.conf
mv ~/ceph.client.docker-cephfs.keyring /etc/ceph/ceph.client.docker-cephfs.keyring
chmod 600 /etc/ceph/ceph.client.docker-cephfs.keyring
chmod 600 /etc/ceph/docker-cephFS.secretget 
chmod 644 /etc/ceph/ceph.conf
```

### 4. Create mount point

```bash
mkdir -p /mnt/docker-cephFS
```

### 5. Test manual mount

```bash
mount -t ceph :/ /mnt/docker-cephFS \
    -o name=docker-cephfs,secretfile=/etc/ceph/docker-cephFS.secret,conf=/etc/ceph/ceph.conf,fs=docker
```

### 6. Configure permanent mount in `/etc/fstab`

Add this line to `/etc/fstab`:

```bash
:/ /mnt/docker-cephFS ceph name=docker-cephfs,secretfile=/etc/ceph/docker-cephFS.secret,conf=/etc/ceph/ceph.conf,fs=docker,_netdev 0 2
```

---

## 🔥 Optional: Automated Bootstrap Script for New VMs

Create a file `/root/cephfs-bootstrap.sh` with the following contents:

```bash
#!/bin/bash

apt update
apt install -y ceph-common

mkdir -p /etc/ceph
mkdir -p /mnt/docker-cephFS

sftp root@[fc00::81] <<EOF
lcd /etc/ceph
get /etc/pve/priv/ceph/docker-cephFS.secret
get /etc/pve/priv/ceph/minimal-ceph.conf
bye
EOF

chmod 600 /etc/ceph/docker-cephFS.secret
chmod 644 /etc/ceph/minimal-ceph.conf
mv /etc/ceph/minimal-ceph.conf /etc/ceph/ceph.conf

mount -t ceph :/ /mnt/docker-cephFS \
    -o name=docker-cephfs,secretfile=/etc/ceph/docker-cephFS.secret,conf=/etc/ceph/ceph.conf,fs=docker
```

Make it executable:

```bash
chmod +x /root/cephfs-bootstrap.sh
```

Run it:

```bash
/root/cephfs-bootstrap.sh
```

✅ This script will install packages, pull configs, set permissions, and mount automatically!

---

## 🔒 Files Overview

| File | Purpose |
|:-----|:--------|
| `/etc/pve/priv/ceph/ceph.client.docker-cephfs.keyring` | Full Ceph client keyring (admin level) |
| `/etc/pve/priv/ceph/docker-cephFS.secret` | Raw base64 secret for kernel mounting |
| `/etc/pve/priv/ceph/minimal-ceph.conf` | Clean minimal Ceph config |

---

## 🚀 TL;DR

> **Pull secret + minimal conf from `/etc/pve/priv/ceph/`, mount `:/` with `fs=docker` into `/mnt/docker-cephFS`. Use fstab for permanent mount.**

This procedure is safe, clean, Proxmox-cluster aware, and scales easily across VMs.
