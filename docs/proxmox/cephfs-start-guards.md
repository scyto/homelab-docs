---
title: "CephFS Start Guards"
---

# CephFS start guards

if cephFS isn't mounted on the host when a docker VM starts, virtiofs shares the
empty mountpoint directory instead, and every stateful container starts from
scratch on an empty directory. two checks stop that: a proxmox hookscript that
blocks the VM start, and a systemd drop-in in each docker VM that stops docker
starting on a missing or empty mount.

| check | catches | runs on |
| --- | --- | --- |
| hookscript on `.donotdelete` | VM starting without cephFS on the host | proxmox host |
| docker-data-guard | docker starting without the mount, or with an empty one | each docker VM |

steps 1 to 3 need the cephFS share from [cephFS via virtiofs](cephfs-virtiofs-passthrough.md).
do step 4 after the stacks' data has moved onto it.

## 1. snippets on ISOs-Templates

the hookscript lives on the `ISOs-Templates` storage, which is cephFS, so all three
nodes see one copy. in `Datacenter > Storage`, select `ISOs-Templates`, click
`Edit` and add `Snippets` to `Content`. then, on a node:

```
ls -d /mnt/pve/ISOs-Templates/snippets
```

- proxmox only creates the `snippets` folder while Snippets is in the storage's
  content. without it there is nowhere to save the script
- one copy on shared storage lets HA start a docker VM on any node
- if proxmox can't reach the script, the VM still doesn't start: proxmox fails it
  with `script ... does not exist`

## 2. the marker and the script { #hookscript }

a proxmox hookscript runs on the host before the VM starts, and a non-zero exit
from its `pre-start` phase stops the start. mine checks that
`/mnt/pve/docker-cephFS` is a ceph mount, then that a marker file on it can be
read within 15 seconds, so a hung cephFS fails the check instead of hanging the
start.

create the marker once, from any node. delete it and no docker VM will start:

```
touch /mnt/pve/docker-cephFS/.donotdelete
```

save the script as `/mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh`:

//// details | check-donotdelete-hook.sh, 28 lines
    type: example

``` { .bash linenums="1" }
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

////

make it executable:

```
chmod +x /mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh
```

- without the execute bit proxmox refuses the start with `script ... is not executable`
- the mount check matters most. a marker check alone would pass if a marker file
  ever landed in the empty directory under the mount point
- `-t ceph` is the kernel client, which proxmox uses for cephFS storage unless you
  turned on fuse. `findmnt -n -o FSTYPE /mnt/pve/docker-cephFS` tells you; if it
  says `fuse.ceph-fuse`, use that instead

## 3. attach it to each docker VM

run this on the node that hosts each docker VM:

```
qm set <vmid> --hookscript ISOs-Templates:snippets/check-donotdelete-hook.sh
qm config <vmid> | grep hookscript
```

- a VM has one hookscript. `qm set` replaces the old reference rather than adding
  a second

## 4. the data guard, after the data moves { #docker-data-guard }

the hookscript only runs when a VM starts. the guard runs in each docker VM
before every docker start, including `systemctl restart docker` and a package
upgrade that restarts the daemon. install it only once the stacks' data is on
cephFS ([migrating](cephfs-virtiofs-passthrough.md#migrating-docker-swarm-stacks-for-exising-stack)):
on an empty cephFS it finds just the two marker files and refuses to start
docker.

create the sentinel once, from any docker VM. the file says what deleting it
does:

```
echo "docker-data-guard sentinel: docker will not start on any swarm node without this file" \
  | sudo tee /mnt/docker-cephFS/.docker-data-ready
```

the guard refuses unless `/mnt/docker-cephFS` is a mountpoint (the mount ran),
holds the sentinel (the right volume) and has at least five entries (it isn't
empty):

//// details | docker-data-guard.sh, 43 lines
    type: example

``` { .sh linenums="1" }
#!/bin/sh
# ExecStartPre guard for docker.service.
#
# Refuses to let dockerd start unless the shared data volume is actually
# present and populated. Without this, a bind mount onto an empty directory
# succeeds and every stateful container initialises itself from scratch:
# MariaDB builds a new database, AdGuard writes a default config, and the
# container reports healthy. That failure is silent and it destroys nothing --
# which is worse, because the real data is still on CephFS and the running
# service is now authoritative for an empty copy of it.
#
# Not CephFS-specific. Same failure on NFS, gluster or any virtiofs share.
#
# Three independent checks, because each catches something the others miss:
#   1. it is a mountpoint      -> the mount unit never ran
#   2. the sentinel exists     -> wrong volume, or a fresh/rebuilt one
#   3. it is populated         -> mounted but empty
#
# Failing here means no Docker at all. That is the intended direction: no
# daemon is better than a daemon serving empty directories.

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

////

save it as `docker-data-guard.sh`, then install it and its drop-in in each docker
VM. nothing restarts; it takes effect the next time docker starts:

```
sudo install -m 0755 -o root -g root docker-data-guard.sh /usr/local/sbin/docker-data-guard
sudo mkdir -p /etc/systemd/system/docker.service.d
printf '[Unit]\nRequiresMountsFor=/mnt/docker-cephFS\n\n[Service]\nExecStartPre=/usr/local/sbin/docker-data-guard\n' \
  | sudo tee /etc/systemd/system/docker.service.d/10-data-guard.conf
sudo systemctl daemon-reload
systemctl show docker.service -p ExecStartPre -p RequiresMountsFor
```

- `RequiresMountsFor=/mnt/docker-cephFS` makes docker start after the mount, and
  not at all if the mount failed. the fstab line has no `nofail`, so a failed
  mount at boot stops the VM in emergency mode
- `ExecStartPre` has no leading `-`, so a failed check stops the start
- the sentinel is a separate file from `.donotdelete`, so changing the hypervisor
  check can't change what docker needs

## if the guard blocks a start

the VM is still reachable over ssh, which doesn't need docker. connect by IP,
because your DNS may be one of the containers that didn't start. then remove the
drop-in and start docker:

```
sudo rm /etc/systemd/system/docker.service.d/10-data-guard.conf
sudo systemctl daemon-reload && sudo systemctl start docker
```

[troubleshooting](../docker/troubleshooting.md#docker-wont-start-after-a-reboot-or-an-upgrade)
shows which check failed. fix the volume, then put the drop-in back.

## checking it

### the hookscript

on each node, run it by hand. this starts nothing:

```
/mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh <vmid> pre-start; echo "exit=$?"
journalctl -t hookscript -n 3
```

expect `exit=0` and the "allowed to start" line. journald stores the `[$VMID]`
part of the tag as the PID, so search with `-t hookscript`;
`-t "hookscript[123]"` finds nothing.

### a refusal

to see it refuse without touching the real marker, run a copy with `MOUNT_BASE`
set to `/tmp`, which isn't a ceph mount:

```
sed 's#^MOUNT_BASE=.*#MOUNT_BASE="/tmp"#' /mnt/pve/ISOs-Templates/snippets/check-donotdelete-hook.sh > /tmp/hooktest.sh
bash /tmp/hooktest.sh <vmid> pre-start; echo "exit=$?"
rm /tmp/hooktest.sh
```

expect `exit=1` and "is not a CephFS mount". the test also logs a "start
blocked" line to the journal. a real refusal shows the same message in the VM's
task log, followed by `hookscript error for <vmid> on pre-start`.

### which VMs have it

this lists every VM with a hookscript, on all nodes. expect one line per docker
VM:

```
grep hookscript /etc/pve/nodes/*/qemu-server/*.conf
```

### the guard

the guard logs to the journal, which a normal user can't read on debian. add
yourself to the `adm` group (`-aG`, not `-G`, see
[install docker](../docker/swarm/install-docker.md#let-your-user-run-docker-without-sudo)),
log out and back in, then after the next docker start:

```
journalctl -u docker -n 20 --no-pager | grep data-guard
```

expect `docker-data-guard: /mnt/docker-cephFS ok (30 entries)`, with your own
count. i haven't seen the guard refuse a start yet.
