#!/bin/bash

set -euo pipefail

SRC=/mnt/cephfs
DIR=${1:-acme_synology}
WORK_BASE=/var/tmp

export PBS_REPOSITORY='cephFS@pbs!cephFS@pbs1.mydomain.com:mnt-pbs'
export PBS_PASSWORD_FILE=/root/.pbs-cephfs-token

snap=$(journalctl -u cephfs-backup.service -o cat --no-pager \
  | sed -n 's/^cephfs-backup: backing up //p' | tail -n 1)
if [[ -z "$snap" || ! -d "$SRC/.snap/$snap" ]]; then
  echo "verify-restore: no snapshot from the journal, or it has been pruned: '$snap'" >&2
  exit 1
fi
if [[ ! -d "$SRC/.snap/$snap/$DIR" ]]; then
  echo "verify-restore: $DIR is not a directory in $snap" >&2
  exit 1
fi

ts=$(proxmox-backup-client snapshot list host/cephfs --ns Files --output-format json \
  | python3 -c 'import json, sys; print(max(s["backup-time"] for s in json.load(sys.stdin)))')
backup="host/cephfs/$(date -u -d "@$ts" +%Y-%m-%dT%H:%M:%SZ)"
echo "backup   $backup"
echo "snapshot $snap"

need=$(du -sk "$SRC/.snap/$snap/$DIR" | cut -f1)
free=$(df -k --output=avail "$WORK_BASE" | tail -n 1 | tr -d ' ')
if (( need + need / 10 > free )); then
  echo "verify-restore: $DIR needs about $((need / 1024)) MiB, $WORK_BASE has $((free / 1024)) MiB free" >&2
  exit 1
fi

work=$(mktemp -d "$WORK_BASE/verify-restore.XXXXXX")
trap 'rm -rf "$work"' EXIT

if ! proxmox-backup-client catalog dump "$backup" --ns Files > "$work/catalog" 2>&1; then
  tail -n 5 "$work/catalog" >&2
  exit 1
fi
echo "entries in the backup:   $(grep -c '^[a-z] "\./' "$work/catalog")"
echo "entries in the snapshot: $(find "$SRC/.snap/$snap" | wc -l)"

proxmox-backup-client restore "$backup" cephfs.pxar "$work/restore" --ns Files --pattern "$DIR/**"

status=0
if diff -rq "$SRC/.snap/$snap/$DIR" "$work/restore/$DIR"; then
  echo "contents of $DIR: identical"
else
  status=1
fi
(cd "$SRC/.snap/$snap" && find "$DIR" -printf '%p %U:%G %m\n' | sort) > "$work/snapshot.list"
(cd "$work/restore" && find "$DIR" -printf '%p %U:%G %m\n' | sort) > "$work/restore.list"
if diff "$work/snapshot.list" "$work/restore.list"; then
  echo "owners and modes of $DIR: identical"
else
  status=1
fi
exit "$status"
