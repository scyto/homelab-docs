---
title: "UPS on the Proxmox Cluster"
---

# ups on the proxmox cluster

all three nodes are on the study UPS. each runs NUT against the UPS card, and
when the battery gets low they shut the cluster down together. checked against
Proxmox VE 9.2, NUT 2.8.1 and Ceph on the thunderbolt mesh.

## what happens in a power cut

every node does the same thing, and no node talks to another. they all watch one
UPS, so they act within a few seconds of each other.

1. the UPS goes on battery
2. when the charge is under 30% or the runtime estimate is under 5 minutes, the
   driver on each node reports low battery, and `upsmon` runs
   `powerfail-shutdown`
3. each node sets four Ceph flags, writes down a time 150 seconds ahead, and
   starts a normal shutdown
4. the node's guests stop. HA stops its own and does not try to start them on
   another node
5. the node waits until the time it wrote down. this is the hold
6. Ceph and corosync stop and the node powers off
7. NUT tells the UPS to turn off. see [the overview](index.md#the-ups-switches-itself-off-and-that-is-what-brings-everything-back)
8. when mains returns the nodes boot, HA starts the guests, and once every OSD is
   up the flags are cleared

the hold is there because Ceph serves storage with two of three nodes up and
stops with one. without it a node whose guests stop quickly would leave Ceph
while another node's guest was still writing.

if mains returns before step 2, nothing happens.

## one cluster setting

**Datacenter** > **Options** > **HA Settings** > **Shutdown Policy**: `freeze`.
or:

```bash
pvesh set /cluster/options --ha shutdown_policy=freeze
```

the default, `conditional`, leaves a powered off node's guests to be started on
another node about two minutes later. that is wrong when all three are going
down.

with `freeze`, powering one node off on purpose no longer moves its guests. for
planned work on one node, put it in maintenance mode first, which migrates them:

```bash
ha-manager crm-command node-maintenance enable pve1
# and when done
ha-manager crm-command node-maintenance disable pve1
```

## NUT on each node

```bash
apt install nut-server nut-client nut-snmp
```

`/etc/nut/ups.conf`, the same on all three:

```text
maxretry = 3

[ups-proxmox]
  driver = snmp-ups
  port = 192.168.1.73
  desc = "Study shelf, PR750LCD"
  mibs = cyberpower
  snmp_version = v3
  secLevel = authPriv
  secName = nutups
  authProtocol = SHA
  privProtocol = AES
  authPassword = <the auth key set on the card>
  privPassword = <the privacy key set on the card>

  ignorelb
  override.battery.charge.low = 30
  override.battery.runtime.low = 300
```

- `ignorelb` makes the driver ignore the UPS's own low battery flag, which comes
  too late, and use the two `override` values instead
- this package starts a driver as soon as a UPS appears in `ups.conf`. do not
  also start the driver by hand to test it: two drivers share one socket, and
  stopping the second one deletes it. `systemctl restart nut-driver@ups-proxmox`
  puts it back

`/etc/nut/nut.conf`: `MODE=netserver` on pve1 and `MODE=standalone` on pve2 and
pve3.

`/etc/nut/upsd.conf`. every node listens on its own LAN address as well as
loopback, with its own address in the second line:

```text
LISTEN 127.0.0.1 3493
LISTEN 192.168.1.81 3493
```

- pve1 is the one PeaNUT and Home Assistant read
- pve2 and pve3 listen on the LAN for the NUT exporter on truenas1, which
  reads each node's own driver for [prometheus](#prometheus). nothing else
  reads them. NUT has no login for reads, and a read can't change anything

[gatus](../monitoring/gatus.md#checking-the-ups-cards-and-nut) connects to
pve1's port every minute as `nut pve1`, asks the study card's web server for
`/` as `ups card study`, and asks prometheus for each node's `OL` flag as
`nut data pve1`, `nut data pve2` and `nut data pve3`. the connect says `upsd`
is up; a data check says that node's driver has fresh data from the card; the
card check is the one that catches a hung card, see
[what watches the cards](index.md#what-watches-the-cards).

`/etc/nut/upsd.users`, with a different password on each node:

```text
[upsmon]
  password = <a password>
  upsmon primary
```

`/etc/nut/upsmon.conf`:

```text
MONITOR ups-proxmox@127.0.0.1 1 upsmon <the upsmon password> primary
MINSUPPLIES 1

SHUTDOWNCMD "/usr/local/sbin/powerfail-shutdown upsmon"

NOTIFYCMD /usr/sbin/upssched
NOTIFYFLAG ONBATT SYSLOG+WALL+EXEC
NOTIFYFLAG ONLINE SYSLOG+WALL+EXEC
NOTIFYFLAG LOWBATT SYSLOG+WALL
NOTIFYFLAG COMMBAD SYSLOG
NOTIFYFLAG COMMOK SYSLOG
NOTIFYFLAG NOCOMM SYSLOG+WALL
NOTIFYFLAG REPLBATT SYSLOG

POLLFREQ 5
POLLFREQALERT 5
HOSTSYNC 15
DEADTIME 15
POWERDOWNFLAG /etc/killpower
RBWARNTIME 43200
NOCOMMWARNTIME 300
FINALDELAY 5
```

use `127.0.0.1`, not `localhost`. `upsd` listens on IPv4 only, and `localhost`
can resolve to `::1` first.

```bash
systemctl restart nut-driver-enumerator.service
systemctl enable --now nut-server.service nut-monitor.service
upsc ups-proxmox@127.0.0.1
```

## prometheus

the NUT exporter from truenas1's
[prometheus-exporters sysext](../truenas/sysexts.md) reads another server when
the scrape names it with `server`. one job per node, in
`/mnt/fast/configs/prometheus/prometheus.yml` on truenas1, prometheus reloads
its config on its own:

<!-- fragment: illustrative -->

```yaml title="/mnt/fast/configs/prometheus/prometheus.yml"
  - job_name: nut-pve1
    metrics_path: /ups_metrics
    scrape_interval: 60s
    params:
      ups: [ups-proxmox]
      server: ["192.168.1.81"]
    static_configs:
      - targets: ["192.168.1.86:9199"]
        labels:
          ups: ups-proxmox
          node: pve1
```

- `nut-pve2` and `nut-pve3` are the same job with `192.168.1.82` and
  `192.168.1.83` as `server`, and `pve2` and `pve3` as `node`
- one job per node, not one for the cluster, because each node shuts itself
  down from its own driver. three nodes read one card, so three green checks
  also say the card answers SNMP to all three
- the exporter puts no label on a series saying which server it came from, so
  each job adds `ups` and `node`. gatus queries by both
- the target is always the exporter on truenas1. `server` is a query
  parameter the exporter reads, and it needs no port: every node listens on
  `3493`. a server on another port needs an exporter of its own: 3.3.0
  ignores its `serverport` parameter
- check the file before prometheus picks it up:

    ```bash
    sudo docker exec ix-prometheus-prometheus-1 promtool check config /config/prometheus.yml
    ```

all three targets are **UP** on prometheus's targets page, and this returns
three series, one per node, each with the value `1`:

```text
network_ups_tools_ups_status{ups="ups-proxmox",flag="OL"}
```

## the shutdown scripts

three scripts in `/usr/local/sbin`, mode 755, and two units in
`/etc/systemd/system`.

`/etc/default/powerfail`:

```text
# 1: log what would be done and change nothing. Leave at 1 until the dry run in
# the test plan has been seen to work on this node. 0 arms it.
DRY_RUN=1

# Seconds this node stays up, counted from the moment the shutdown is ordered,
# after its own guests have stopped. Must be the same on every node, and longer
# than the slowest guest in the cluster takes to shut down.
HOLD_SECONDS=150
```

`/usr/local/sbin/powerfail-shutdown`, which `upsmon` runs as root:

```bash
#!/bin/bash
# Shut this node down because the UPS feeding the cluster is on battery.
#
# upsmon runs this as root, as its SHUTDOWNCMD, on every node at about the same
# moment: all three watch the same UPS. Nothing here talks to another node. The
# clock is what coordinates them.
#
# What it does, in order:
#   1. writes the time until which this node must stay up, for powerfail-hold
#   2. sets the Ceph flags that stop the cluster reacting to nodes going away
#   3. starts a normal shutdown
#
# Every step is safe to run three times, because every node runs it.

set -u

STATE_DIR=/var/lib/powerfail
FLAGS="noout norebalance norecover nobackfill"

# How long after this moment the node stays up once its own guests have stopped,
# so that no node leaves Ceph while another node's guest is still writing.
HOLD_SECONDS=150
# 1 means log what would be done and change nothing. Installs start this way.
DRY_RUN=1

# shellcheck disable=SC1091
[ -r /etc/default/powerfail ] && . /etc/default/powerfail

log() { logger -t powerfail -- "$*"; echo "powerfail: $*" >&2; }

reason="${1:-unspecified}"
log "shutdown requested (reason: ${reason}, hold ${HOLD_SECONDS}s, dry run ${DRY_RUN})"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY RUN: would write ${STATE_DIR}/hold-until, set Ceph flags [${FLAGS}], and shut down"
  exit 0
fi

mkdir -p "$STATE_DIR"

# First, before anything that can hang: if Ceph does not answer, the hold must
# still be in place when the shutdown reaches it.
deadline=$(( $(date +%s) + HOLD_SECONDS ))
echo "$deadline" > "${STATE_DIR}/hold-until"

# The marker powerfail-resume looks for on the next boot. Written before the
# flags are set, so a flag is never left set with nothing recording why.
date -Is > "${STATE_DIR}/flags-set"

for flag in $FLAGS; do
  if timeout 20 ceph osd set "$flag" >/dev/null 2>&1; then
    log "ceph flag set: ${flag}"
  else
    log "could not set ceph flag ${flag}; continuing"
  fi
done

log "starting shutdown; this node holds until $(date -d "@${deadline}" +%H:%M:%S) after its guests stop"
/sbin/shutdown -h +0 "UPS on battery: cluster shutdown"
```

`/usr/local/sbin/powerfail-hold`:

```bash
#!/bin/bash
# Keep this node up until the hold deadline. Run by powerfail-hold.service as it
# stops, which systemd orders after the guests and HA have stopped and before
# Ceph, the cluster filesystem and the network stop.
#
# On an ordinary shutdown or reboot there is no deadline file, and this exits at
# once.

set -u

DEADLINE_FILE=/var/lib/powerfail/hold-until
# A deadline further away than this is not believed: the file is stale or wrong,
# and a node must never refuse to shut down because of it.
MAX_WAIT_SECONDS=900

log() { logger -t powerfail -- "$*"; echo "powerfail: $*" >&2; }

[ -r "$DEADLINE_FILE" ] || exit 0

deadline=$(tr -cd '0-9' < "$DEADLINE_FILE")
now=$(date +%s)
if [ -z "$deadline" ]; then
  log "hold: ${DEADLINE_FILE} holds no time; not holding"
  exit 0
fi

remaining=$(( deadline - now ))
if [ "$remaining" -le 0 ]; then
  log "hold: deadline already passed ${remaining#-}s ago; not holding"
  exit 0
fi
if [ "$remaining" -gt "$MAX_WAIT_SECONDS" ]; then
  log "hold: deadline is ${remaining}s away, more than ${MAX_WAIT_SECONDS}s; not believed, not holding"
  exit 0
fi

log "hold: guests on this node have stopped; keeping Ceph up for ${remaining}s more"
sleep "$remaining"
log "hold: released"
exit 0
```

`/etc/systemd/system/powerfail-hold.service`. stop order is the reverse of start
order, so starting after Ceph and before the guests means it stops after the
guests and before Ceph:

```text
[Unit]
Description=Hold this node up until every node's guests have stopped (power failure only)
# Stop order is the reverse of start order. Starting after Ceph, the cluster
# filesystem and the network means this stops before they do. Starting before
# the guests and HA means this stops after they have.
After=ceph.target ceph-osd.target ceph-mon.target ceph-mgr.target ceph-mds.target
After=pve-cluster.service corosync.service network-online.target
Before=pve-guests.service pve-ha-lrm.service pve-ha-crm.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/true
ExecStop=/usr/local/sbin/powerfail-hold
# Longer than the longest hold powerfail-hold will honour.
TimeoutStopSec=1000

[Install]
WantedBy=multi-user.target
```

`/usr/local/sbin/powerfail-resume`:

```bash
#!/bin/bash
# After a power-failure shutdown, clear the Ceph flags once the cluster is whole.
#
# powerfail-resume.service runs this at boot, only when the marker left by
# powerfail-shutdown exists. Every node runs it. Clearing a flag that is already
# clear does nothing.
#
# It waits for every OSD to be up before clearing anything. If that does not
# happen in time, a node or a disk has not come back, and the flags are left set
# on purpose: with them set, Ceph does not start moving data around to cover for
# something that may only be slow to boot. That case needs a person.
#
# This procedure owns the four flags below. If one of them had been set by hand
# for other maintenance before the power failed, it is cleared here too.

set -u

STATE_DIR=/var/lib/powerfail
FLAGS="nobackfill norecover norebalance noout"
WAIT_SECONDS=1800
POLL_SECONDS=15

log() { logger -t powerfail -- "$*"; echo "powerfail: $*" >&2; }

[ -e "${STATE_DIR}/flags-set" ] || exit 0

# Prints "<up> <total>", or nothing if Ceph does not answer. Plain grep, so the
# script needs nothing that is not on a bare node.
osd_counts() {
  local json up total
  json=$(timeout 20 ceph osd stat --format json 2>/dev/null) || return 0
  up=$(printf '%s' "$json" | grep -o '"num_up_osds": *[0-9]*' | grep -o '[0-9]*$' | head -1)
  total=$(printf '%s' "$json" | grep -o '"num_osds": *[0-9]*' | grep -o '[0-9]*$' | head -1)
  [ -n "$up" ] && [ -n "$total" ] && echo "$up $total"
}

log "resume: waiting up to ${WAIT_SECONDS}s for every OSD to be up"
waited=0
while [ "$waited" -lt "$WAIT_SECONDS" ]; do
  read -r up total <<< "$(osd_counts)"
  if [ -n "${up:-}" ] && [ -n "${total:-}" ] && [ "$total" -gt 0 ] && [ "$up" -eq "$total" ]; then
    for flag in $FLAGS; do
      if timeout 20 ceph osd unset "$flag" >/dev/null 2>&1; then
        log "resume: ceph flag cleared: ${flag}"
      else
        log "resume: could not clear ceph flag ${flag}"
      fi
    done
    rm -f "${STATE_DIR}/flags-set" "${STATE_DIR}/hold-until"
    log "resume: all ${total} OSDs are up; flags cleared"
    exit 0
  fi
  sleep "$POLL_SECONDS"
  waited=$(( waited + POLL_SECONDS ))
done

log "resume: only ${up:-?} of ${total:-?} OSDs are up after ${WAIT_SECONDS}s; LEAVING THE CEPH FLAGS SET. Check the cluster, then: for f in ${FLAGS}; do ceph osd unset \$f; done; rm ${STATE_DIR}/flags-set"
exit 1
```

`/etc/systemd/system/powerfail-resume.service`:

```text
[Unit]
Description=Clear the Ceph flags set by a power-failure shutdown, once the cluster is whole
After=ceph.target pve-cluster.service network-online.target
Wants=network-online.target
ConditionPathExists=/var/lib/powerfail/flags-set

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/powerfail-resume
# Longer than the wait inside the script.
TimeoutStartSec=2100

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now powerfail-hold.service
systemctl enable powerfail-resume.service
```

on an ordinary shutdown or reboot there is no deadline file, so the hold exits
at once, and no marker file, so the resume unit does not run.

if the OSDs are not all up 30 minutes after boot, `powerfail-resume` leaves the
flags set and fails. a node or a disk has not come back, and that needs a
person. the log says what to run.

## testing it

read the log after each step with `journalctl -t powerfail`.

1. with `DRY_RUN=1`, `upsmon -c fsd` should log `DRY RUN: would write ...` and
   change nothing. it leaves two things behind: the UPS shows `FSD` to every
   reader, and `/etc/killpower` exists. clean up with:

    ```bash
    rm -f /etc/killpower
    systemctl restart nut-server.service
    systemctl restart nut-monitor.service
    ```

2. check the hold is in the right place with one planned reboot:

    ```bash
    mkdir -p /var/lib/powerfail
    echo $(( $(date +%s) + 120 )) > /var/lib/powerfail/hold-until
    reboot
    ```

    then in `journalctl -b -1`, in this order: `pve-guests`, `pve-ha-lrm` and
    `pve-ha-crm` stopped, the `hold:` lines, then the Ceph daemons and corosync
    stopping. remove the file afterwards

3. check the flags are cleared:

    ```bash
    ceph osd set noout
    mkdir -p /var/lib/powerfail && touch /var/lib/powerfail/flags-set
    systemctl start powerfail-resume.service
    ceph osd dump | grep ^flags
    ```

4. set `DRY_RUN=0` on every node and pull the mains

## the full test, 2026-10-01

with the 5 minute timer this page used before the thresholds:

| time | |
| --- | --- |
| 21:37:31 | UPS on battery |
| 21:42:33 | all three nodes ordered the shutdown, within 5 seconds of each other |
| 21:44:00 | last guest stopped |
| 21:45:07 to 21:45:12 | the three holds released |
| 21:45:20 | all three nodes off |
| 21:49:16 to 21:49:25 | all three booted after mains returned |
| 21:51:13 | every OSD up, flags cleared |

it ordered the shutdown with 93% of the battery left, which is why it now waits
for 30% or 5 minutes of runtime. the thresholds have not had a full test yet.

how long each guest took to stop:

| guest | seconds |
| --- | --- |
| homeassistant | 62 |
| winserver01, winserver02 | 29, 26 |
| docker01, docker02, docker03 | 16 to 21 |
| the two containers | 8 to 10 |
