---
title: "Hypervisor Host Based CephFS pass through with VirtioFS"
source_gist: https://gist.github.com/scyto/1b526c38b9c7f7dca58ca71052653820
comments: true
---

# Hypervisor Host Based CephFS pass through with VirtioFS

## Using VirtioFS backed by CephFS for bind mounts
This is currently a work-in-progress documentation - rough notes for me, maybe missing a lot or wrong

The idea is to replace GlusterFS running inside the VM with storage on my cephfs cluster.  This is my proxmox cluster and it runs both the storage and is the hypervisor for my docker VMs.

Other possible approaches:
- ceph fuse clien in VM to mount cephFS or CephRBD over IP
- use of ceph docker volume plugin (no useable version of this yet exists but it is being worked on) 

Assumptions:
- I already have a working Ceph Cluster - this will not be documented in this gist. See my proxmox gist for a working example.
- this is for proxmox as a hypervisor+ceph cluster and the VMs are hosted on the same proxmox that is the ceph cluster

## Workflow

### Create a new cephFS on the proxmox cluster
I created one called docker

![image](../assets/img/115a4e8cd9c2.png)

The storage ID is docker-cephFS (i chose this name as I will play with ceph in a varity of other ways too)

![image](../assets/img/06e0f89525e3.png)


### Add this to directory mappings

![image](../assets/img/88fcbaeb3aba.png)


### Configure docker host VMs to pass through

![image](../assets/img/bbc5bdd4e27b.png)


### Stop the VMs starting without cephFS (hookscript) { #hookscript }

if cephFS isn't mounted on the host when a docker VM starts, virtiofs shares the
empty mountpoint directory instead. the VM boots, docker starts, and every
stateful container initialises against an empty directory.

a proxmox hookscript runs on the host before the VM starts, and a non-zero exit
from its `pre-start` phase aborts the start. mine checks two things:

1. `/mnt/pve/docker-cephFS` is a ceph mount, not just the empty directory
2. a marker file on cephFS can be read, under a timeout so a hung cephFS fails the
   check instead of hanging the start

create the marker once, from any node:

```
touch /mnt/pve/docker-cephFS/.donotdelete
```

delete it and no docker VM will start.

save the script where every node can see it, i use the `ISOs-Templates` storage,
as `/mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh`:

```bash
#!/bin/bash
# check-donotdelete-hook.sh - blocks VM start unless CephFS is mounted on the host
set -e

VMID="$1"
PHASE="$2"

MOUNT_BASE="/mnt/pve/docker-cephFS"
MARKER_PATH="${MOUNT_BASE}/.donotdelete"

log() { logger -t "hookscript[$VMID]" "$@" || true; }

case "$PHASE" in
  pre-start)
    if ! findmnt -t ceph -M "$MOUNT_BASE" >/dev/null; then
      log "VM $VMID start blocked: ${MOUNT_BASE} is not a CephFS mount."
      echo "VM $VMID start blocked: ${MOUNT_BASE} is not a CephFS mount."
      exit 1
    fi
    if ! timeout 15 stat "$MARKER_PATH" >/dev/null 2>&1; then
      log "VM $VMID start blocked: ${MARKER_PATH} missing or CephFS unresponsive."
      echo "VM $VMID start blocked: ${MARKER_PATH} missing or CephFS unresponsive."
      exit 1
    fi
    log "VM $VMID allowed to start: CephFS mounted and marker present."
    ;;
esac
exit 0
```

notes on it:

- the mount check is the main one. a marker check on its own passes if a marker
  ever ends up in the bare directory underneath the mount.
- `-t ceph` is the kernel client, which is what proxmox uses for cephFS storage
  unless you turned on fuse. `findmnt -n -o FSTYPE /mnt/pve/docker-cephFS` tells
  you; if it says `fuse.ceph-fuse`, use that instead.
- `|| true` on `logger` is there because of `set -e`. without it a logging
  failure would block the start.
- the `[$VMID]` in the tag gets stored as the log entry's PID, so search the
  journal with `-t hookscript`. `-t "hookscript[123]"` finds nothing.

make it executable. proxmox refuses to run a hookscript without the execute bit
(`script ... is not executable`):

```
chmod +x /mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh
```

attach it to each docker VM, then check it took:

```
qm set <vmid> --hookscript ISOs-Templates:snippets/check-donotdelete-hook.sh
qm config <vmid> | grep hookscript
```

a VM has one hookscript, `qm set` replaces the old reference rather than adding a
second.

test it without restarting anything:

```
/mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh <vmid> pre-start; echo "exit=$?"
journalctl -t hookscript -n 3
```

expect `exit=0` and the "allowed to start" line.

test the refusal too, on a copy pointed at a directory that isn't a ceph mount, so
the real marker is never touched:

```
sed 's#^MOUNT_BASE=.*#MOUNT_BASE="/tmp"#' /mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh > /tmp/hooktest.sh
bash /tmp/hooktest.sh <vmid> pre-start; echo "exit=$?"
rm /tmp/hooktest.sh
```

expect `exit=1` and "is not a CephFS mount". it logs a blocked line to the
journal as well, that's the test, not a real refusal.

when a real start is blocked, the task log shows the script's message and
`hookscript error for <vmid> on pre-start`.

my old script was `cephFS-hookscript.pl` and only checked the marker. delete it
once nothing references it:

```
grep hookscript /etc/pve/nodes/*/qemu-server/*.conf
```

one thing to know about where it lives: `ISOs-Templates` is itself cephFS. if
proxmox can't reach the script the VM still won't start, the error just comes
from proxmox (`script ... does not exist`) instead of from the script. if you'd
rather the check didn't depend on ceph at all, keep a copy in a node-local
snippets directory instead, on all three nodes, or HA can't start the VM on the
node that's missing it.


### In *each* VM

In each VM

- `sudo mkdir /mnt/docker-cephFS/`
- `sudo nano /etc/fstab`
  - add ```#for virtiofs mapping
docker-cephFS  /mnt/docker-cephFS  virtiofs  defaults  0  0```
  - save the file
- `sudo systemctl daemon-reload`
- `sudo mount -a`

no `nofail` on that fstab line, on purpose. if the mount fails the VM stops in
emergency mode rather than booting without it.

### Make docker wait for the mount, and refuse an empty one { #docker-data-guard }

the hookscript only covers the VM starting. it can't see docker starting again
later: a `systemctl restart docker`, a package upgrade restarting the daemon, a
remount. and a bind onto an empty directory succeeds, docker doesn't care that
`/mnt/docker-cephFS/npm_data` has nothing in it.

| check | catches | runs on |
| --- | --- | --- |
| hookscript on `.donotdelete` | VM starting without cephFS on the host | proxmox host |
| docker-data-guard | docker starting without the mount, or with an empty one | each VM |

each node gets a systemd drop-in for `docker.service` with two lines:

- `RequiresMountsFor=/mnt/docker-cephFS` makes docker start after the mount, and
  not at all if the mount failed. the ordering already happened to come in via
  `basic.target`, this states it.
- `ExecStartPre=/usr/local/sbin/docker-data-guard` runs a check before `dockerd`.
  no leading `-`, so a failed check aborts the start.

the check, saved as `docker-data-guard.sh`:

```sh
#!/bin/sh
# ExecStartPre guard for docker.service. refuses to let dockerd start unless
# the shared data volume is mounted, carries the sentinel, and is populated.

set -eu

MOUNT="${DOCKER_DATA_MOUNT:-/mnt/docker-cephFS}"
SENTINEL="$MOUNT/.docker-data-ready"
MIN_ENTRIES="${DOCKER_DATA_MIN_ENTRIES:-5}"

die() {
    echo "docker-data-guard: REFUSING TO START DOCKER: $*" >&2
    echo "docker-data-guard: containers would bind onto empty directories and" >&2
    echo "docker-data-guard: re-initialise themselves. Fix the volume first." >&2
    exit 1
}

mountpoint -q "$MOUNT" || die "$MOUNT is not a mountpoint"

[ -e "$SENTINEL" ] || die "$SENTINEL missing -- wrong volume, or not populated"

entries=$(ls -A "$MOUNT" 2>/dev/null | wc -l)
[ "$entries" -ge "$MIN_ENTRIES" ] || \
    die "$MOUNT has only $entries entries (expected >= $MIN_ENTRIES)"

echo "docker-data-guard: $MOUNT ok ($entries entries)"
```

three checks because each catches something the others miss: the mount never
ran, the wrong or a rebuilt volume is mounted, or it's mounted but empty.

the sentinel is `/mnt/docker-cephFS/.docker-data-ready`. it's a separate file from
`.donotdelete` on purpose, so changing the hypervisor check can't change what
docker needs. create it once and put a line in it saying what it's for, so whoever
finds it knows what deleting it does:

```
echo "docker-data-guard sentinel: docker will not start on any swarm node without this file" \
  | sudo tee /mnt/docker-cephFS/.docker-data-ready
```

install on each node. nothing restarts, it applies next time docker starts:

```
sudo install -m 0755 -o root -g root docker-data-guard.sh /usr/local/sbin/docker-data-guard
sudo mkdir -p /etc/systemd/system/docker.service.d
printf '[Unit]\nRequiresMountsFor=/mnt/docker-cephFS\n\n[Service]\nExecStartPre=/usr/local/sbin/docker-data-guard\n' \
  | sudo tee /etc/systemd/system/docker.service.d/10-data-guard.conf
sudo systemctl daemon-reload
systemctl show docker.service -p ExecStartPre -p RequiresMountsFor
```

don't have anything in the start path `mkdir` the app directories. a missing
directory should make the volume fail to mount, not get replaced with an empty one.
create them on cephFS once, see below.

the guard's output goes to the journal, which a normal user can't read on debian.
add yourself to `adm` (`-aG`, not `-G`, see [install docker](../docker-swarm/install-docker.md)),
log out and back in, then:

```
journalctl -u docker -n 20 --no-pager | grep data-guard
# docker-data-guard: /mnt/docker-cephFS ok (30 entries)
```

if it ever blocks a start, ssh doesn't depend on docker so the node is still
reachable. use the IP, your dns might be running on that node:

```
sudo rm /etc/systemd/system/docker.service.d/10-data-guard.conf
sudo systemctl daemon-reload && sudo systemctl start docker
```

fix the volume before putting the drop-in back.

so far i've only seen it let a healthy node through (a docker03 restart logged
`ok (30 entries)` and every service came back). i haven't tested the refusal yet.

## Migrating Docker Swarm Stacks for exising Stack

basically its

- stop the stack
- mv the data from /mnt/gluster-vol1/dirname to /mnt/docker-cephFS/dirname

- Edit the stack to change the volume defitions from my gluster defition to a local volume - this mean no editing of the service volme lines

Example from my wordpress stack

```
volumes:
  dbdata:
    driver: gluster-vol1
  www:
    driver: gluster-vol1

```

to

```
volumes:
  dbdata:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/wordpress_dbdata"
      o: bind

  www:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/wordpress_www"
      o: bind

```

- triple check everything
- make sure each `device` directory already exists on cephFS. if one is missing the
  task fails to start, which is what you want, don't have anything create it for you
- restart the stack
- check each volume really is the bind, on the node running the task:

```
docker volume inspect wordpress_dbdata --format '{{json .Options}}'
findmnt /var/lib/docker/volumes/wordpress_dbdata/_data
```

the options must show `device`, `o` and `type`, and findmnt must show
`docker-cephFS[/wordpress_dbdata] virtiofs`. the bind is only mounted while a
container on that node is using it, so findmnt prints nothing on the other nodes.

if you get an error about the volumen already being defined you may need to delete the old volume defition by had - thi can easily be done  in portainer or using the docker volume command

if there's no error but the options come back `null` or `{}`, a plain volume with
that name already existed on the node and docker reused it, ignoring the new
`driver_opts`. the container has been writing to that node's local disk, not
cephFS. fix in [troubleshooting](../docker-swarm/troubleshooting.md#a-volume-moved-to-cephfs-is-still-on-local-disk).

## Backup
havent figured out an ideal strategy for backing up the cephFS on the host or from the vm - with glsuter the bricks were stored on a dedicated vdisk - this was backed up as part of the pbs backup of the vm

As the virtioFS is not presented as a disk this doesn't happen (this is reasonable as the cephFS is not VM specific)
