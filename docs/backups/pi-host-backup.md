---
title: "Raspberry Pi to PBS"
---

# raspberry pi to PBS

my Z-Wave pi backs itself up to [PBS](pbs-server.md) every hour, as a host
backup in the `Hosts` namespace. this is how.

## the client on arm64

Proxmox only publishes `proxmox-backup-client` for amd64. Debian does not package
it either. for a pi that leaves community builds, and the one i use is
[wofferl/proxmox-backup-arm64](https://github.com/wofferl/proxmox-backup-arm64),
which builds the Proxmox sources for arm64 and publishes Debian packages for
bookworm and trixie. i use the static client, it has no library dependencies.

check the pi is 64 bit first. `armhf` means a 32 bit OS and this will not run:

```
dpkg --print-architecture
```

download, check it is the file GitHub has for that release, install:

```
cd /tmp
curl -fLO https://github.com/wofferl/proxmox-backup-arm64/releases/download/4.2.5-1/proxmox-backup-client-static_4.2.5-1_arm64.deb
echo "0c7f9be14286ddaeef2a2644d1515051ef94759336a980b34579105062221848  proxmox-backup-client-static_4.2.5-1_arm64.deb" | sha256sum -c
sudo apt install ./proxmox-backup-client-static_4.2.5-1_arm64.deb
proxmox-backup-client version
```

the checksum is the one GitHub publishes for that release asset. it proves you got
the file that was uploaded, not that the build is trustworthy. if that matters to
you, the same repo's `./build.sh client` builds it from source. match the client
version to your PBS.

## 1. a user and token for this machine only

on PBS. one user and token per machine, never shared: PBS only lets a
`DatastoreBackup` token touch backup groups it owns, so separate tokens keep one
machine from reading another's backups, and a lost pi means deleting one token.

```
proxmox-backup-manager user create pi-zwave01@pbs --comment "pi-zwave01 host backups"
proxmox-backup-manager acl update /datastore/mnt-pbs/Hosts DatastoreBackup --auth-id pi-zwave01@pbs
proxmox-backup-manager user generate-token pi-zwave01@pbs backup
proxmox-backup-manager acl update /datastore/mnt-pbs/Hosts DatastoreBackup --auth-id 'pi-zwave01@pbs!backup'
```

- the user and the token both need the ACL, a token can never do more than its
  user
- the ACL is on the `Hosts` namespace only, not the whole datastore
- `generate-token` shows the secret once. keep it somewhere safe before you close
  the shell

**taking over an existing backup group.** if the machine backed up before under
another token, its group still belongs to that token and the first run fails with

```
backup owner check failed (pi-zwave01@pbs!backup != <old owner>)
```

change the owner in the PBS UI: datastore, Content, namespace `Hosts`, the person
icon on the group. the old snapshots stay in the group.

## 2. the token file

keep it somewhere that is not backed up, so a copy of the credential does not end
up inside the backups it protects:

```
sudo install -d -m 700 /var/lib/pbs-backup
sudo nano /var/lib/pbs-backup/token          # paste the secret, save
sudo chmod 600 /var/lib/pbs-backup/token
```

the file holds the secret only, not the `user!token` part. the client reads only
the first line, so the newline nano adds is fine.

## 3. the script

`/usr/local/sbin/pbs-backup`, mode `700`:

```bash
#!/bin/bash
set -euo pipefail
export PBS_REPOSITORY='pi-zwave01@pbs!backup@pbs1.mydomain.com:mnt-pbs'
export PBS_PASSWORD_FILE=/var/lib/pbs-backup/token
proxmox-backup-client backup \
  docker-data.pxar:/docker-data \
  etc.pxar:/etc \
  usr-local.pxar:/usr/local \
  root.pxar:/root \
  home.pxar:/home \
  --ns Hosts --backup-id pi-zwave01
```

what the archives are for:

| archive | why |
| --- | --- |
| `docker-data.pxar` | everything the containers keep. this is the one you restore |
| `etc.pxar`, `usr-local.pxar`, `root.pxar`, `home.pxar` | reference copies of config, for pulling out a single file. not for restoring over a fresh install |

i don't back up the whole filesystem. restoring `/usr` or package
state file by file over a running system does not work well, docker's images come
back from their registries, and the stacks come back from git. the plan is to
rebuild the pi from a script and restore `docker-data.pxar`.

the single quotes keep an interactive bash from treating the `!` in
`pi-zwave01@pbs!backup` as history expansion.

## 4. an hourly timer

`/etc/systemd/system/pbs-backup.service`:

```ini
[Unit]
Description=Back up pi-zwave01 to PBS
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/pbs-backup
```

`/etc/systemd/system/pbs-backup.timer`:

```ini
[Timer]
OnCalendar=hourly
RandomizedDelaySec=5m
Persistent=true

[Install]
WantedBy=timers.target
```

run it once by hand before turning the timer on:

```
sudo systemctl daemon-reload
sudo systemctl start pbs-backup.service
journalctl -u pbs-backup -n 30 --no-pager
sudo systemctl enable --now pbs-backup.timer
```

a timer rather than cron because the output lands in the journal, and
`Persistent=true` runs a missed backup when the pi comes back up.

## 5. prove it restores

a clean exit only proves the upload finished. this proves the backup is usable.

```
export PBS_REPOSITORY='pi-zwave01@pbs!backup@pbs1.mydomain.com:mnt-pbs'
export PBS_PASSWORD_FILE=/var/lib/pbs-backup/token
SNAP='host/pi-zwave01/<snapshot time>'

du -sh --apparent-size /docker-data
proxmox-backup-client catalog dump "$SNAP" --ns Hosts 2>&1 | grep -E 'configuration.yaml|ser2net.yaml'
proxmox-backup-client restore "$SNAP" docker-data.pxar /tmp/restore-test --ns Hosts
diff -rq /docker-data /tmp/restore-test | wc -l
rm -rf /tmp/restore-test
```

- the size should match what the backup log reported
- `catalog dump` writes to stderr, hence the `2>&1`, or the grep sees nothing
- a handful of differences is normal, files the apps wrote since the backup. on
  mine it was six, all Z-Wave's network cache and today's logs

mine: 20 MB of `/docker-data`, 6 MB compressed, under two seconds to back up, half
a second to restore.
