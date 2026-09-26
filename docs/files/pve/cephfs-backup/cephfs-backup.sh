#!/bin/bash

set -euo pipefail

SRC=/mnt/cephfs
MAX_AGE=$((2 * 60 * 60))
MAX_SKEW=60

export PBS_REPOSITORY='cephFS@pbs!cephFS@pbs1.mydomain.com:mnt-pbs'
export PBS_PASSWORD_FILE=/root/.pbs-cephfs-token

GATUS_URL="http://192.168.1.45:8085"
GATUS_ENDPOINT="plumbing_cephfs-backup"
GATUS_TOKEN_FILE=/root/.gatus-cephfs-backup-token

log() { echo "cephfs-backup: $*"; }

gatus_report() {
  local ok=$1 err=${2:-}
  if [[ ! -r "$GATUS_TOKEN_FILE" ]]; then
    log "no gatus token at $GATUS_TOKEN_FILE: result not reported"
    return 0
  fi
  printf 'Authorization: Bearer %s\n' "$(cat "$GATUS_TOKEN_FILE")" \
    | curl -fsS -m 20 -o /dev/null -X POST -H @- -G \
        --data-urlencode "success=$ok" --data-urlencode "error=$err" \
        --data-urlencode "duration=${SECONDS}s" \
        "$GATUS_URL/api/v1/endpoints/$GATUS_ENDPOINT/external" \
    || log "could not report the result to gatus"
}

reported=0
on_exit() {
  local rc=$?
  if (( rc != 0 && reported == 0 )); then
    gatus_report false "exit $rc"
  fi
}
trap on_exit EXIT

fail() {
  log "FAILED: $*"
  gatus_report false "$*"
  reported=1
  exit 1
}

[[ -d "$SRC/.snap" ]] || fail "$SRC/.snap not found: is cephFS mounted on this node?"

newest="" newest_ts=0
for dir in "$SRC"/.snap/scheduled-*; do
  [[ -d "$dir" ]] || continue
  s=${dir##*/scheduled-}                      # 2026-09-25-13_00_00_PDT
  when="${s:0:10} ${s:11:2}:${s:14:2}:${s:17:2} ${s:20}"
  if ! ts=$(date -d "$when" +%s 2>/dev/null); then
    log "skipping ${dir##*/}: its name is not a time"
    continue
  fi
  if (( ts > newest_ts )); then
    newest=$dir
    newest_ts=$ts
  fi
done

[[ -n "$newest" ]] || fail "no scheduled snapshot under $SRC/.snap"
age=$(( $(date +%s) - newest_ts ))
(( age >= -MAX_SKEW )) \
  || fail "newest snapshot ${newest##*/} is dated $(( -age / 60 )) minutes in the future: is the ceph-mgr's clock right?"
(( age <= MAX_AGE )) \
  || fail "newest snapshot ${newest##*/} is $(( age / 60 )) minutes old: is snap_schedule running?"
[[ -e "$newest/.donotdelete" ]] || fail "${newest##*/} has no .donotdelete: not the docker cephFS"

log "backing up ${newest##*/}"
proxmox-backup-client backup "cephfs.pxar:$newest" \
  --ns Files \
  --backup-id cephfs \
  --change-detection-mode=metadata

gatus_report true
reported=1
log "done in ${SECONDS}s"
