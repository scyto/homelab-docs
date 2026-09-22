---
title: "Glances"
---

# glances on every host

[glances](https://github.com/nicolargo/glances) on all nine hosts: the six docker hosts in a container, the three proxmox nodes on the host itself. every one runs 4.5.6 on port `61208`, so the [dashboard](homepage.md)'s tiles and the [gatus](gatus.md) checks have one shape for all of them. clicking a tile opens that host's glances.

## on the docker hosts

glances in a container reports the container, not the host: its own network interfaces, its own OS name, its own mounts. four things fix that.

**host networking**, so it sees the host's real interfaces. on the swarm that's the built-in `host` network, attached as an external network; on a standalone host, `network_mode: host`.

```yaml
services:
  glances:
    networks:
      - hostnet
networks:
  hostnet:
    external: true
    name: host
```

**the host's `/etc/os-release`**, bound read-only, or it reports the image's alpine. synology has no `os-release`, so syn02's stack builds one from DSM's `/etc/VERSION` at start.

**an empty directory per filesystem**, for disks. glances lists the container's own mounts, and a bind of an empty directory reports the filesystem that directory lives on. one on the root filesystem, one on cephfs, bound read-only under `/host/`:

```yaml
      - type: bind
        source: /var/lib/glances-probe
        target: /host/root
        read_only: true
      - type: bind
        source: /mnt/docker-cephFS/.glances-probe
        target: /host/cephfs
        read_only: true
```

the directories have to exist first. a missing source fails the task, which is what i want.

**a config override at start**, so it shows only those and hides the container plumbing. cephfs reaches the VMs as `virtiofs`, which glances hides unless it's allowed:

```ini
[network]
hide=veth.*,docker.*,br-.*,lo
[fs]
show=/host/.*
allow=virtiofs
```

the entrypoint edits the image's own `/etc/glances/glances.conf` in place, keeping its defaults, then starts glances.

- on the swarm it's `mode: global`, one per node, and it has no healthcheck: gatus checks it instead
- no docker socket and no `pid: host`, so no container list and no host-wide process list. [dozzle](dozzle.md) and portainer cover containers

## on the proxmox nodes

on the host, as a systemd service, in its own python venv pinned to 4.5.6.

- **not an LXC.** proxmox gives every container LXCFS, so `/proc` shows the container's allowance, not the node's, and it has its own network namespace and root filesystem. it would report the LXC
- **not debian's `glances` package.** debian strips the prebuilt web UI, because it can't be rebuilt from source with debian's own tools, and has marked the bug won't-fix. there'd be no page for the tile to open

as root on each node:

```
apt-get update
apt-get install --yes python3-venv
useradd --system --home-dir /var/lib/glances --no-create-home --shell /usr/sbin/nologin glances
python3 -m venv /opt/glances
/opt/glances/bin/pip install --disable-pip-version-check 'glances[web]==4.5.6'
mkdir --parents /etc/glances
cat > /etc/glances/glances.conf <<'EOF'
[network]
hide=lo,tap.*,fwbr.*,fwpr.*,fwln.*,veth.*

[fs]
hide=/boot.*,/var/lib/glances,/var/tmp
EOF
echo 'GLANCES_BIND=192.168.1.81' > /etc/default/glances
```

use each node's own address in `GLANCES_BIND`. then the unit:

```
cat > /etc/systemd/system/glances.service <<'EOF'
[Unit]
Description=Glances web server (REST API and web UI)
Wants=network-online.target
After=network-online.target

[Service]
Type=exec
User=glances
Group=glances
EnvironmentFile=/etc/default/glances
Environment=HOME=/var/lib/glances
StateDirectory=glances
ExecStart=/opt/glances/bin/glances --config /etc/glances/glances.conf --webserver --bind ${GLANCES_BIND} --port 61208 --disable-autodiscover
Restart=on-failure
RestartSec=10s
NoNewPrivileges=yes
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes
SystemCallArchitectures=native
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now glances.service
sleep 5
curl --silent http://$(sed -n 's/^GLANCES_BIND=//p' /etc/default/glances):61208/api/4/quicklook/mem; echo
```

- the last line must print a memory figure above zero. `systemctl status` straight after starting reads active even when the bind is about to fail
- it listens on the node's lan address only, runs as its own user with no capabilities, and can write only its state directory and a private `/tmp`
- the hidden interfaces are proxmox's per-guest `tap` and firewall bridges; the hidden filesystems are the service sandbox's own mounts
- after a proxmox major upgrade, which brings a new python, rebuild the venv: delete `/opt/glances` and run the `venv` and `pip` lines again

## one check for all nine

```yaml
    url: "http://192.168.1.81:61208/api/4/quicklook"
    conditions:
      - "[STATUS] == 200"
      - "[BODY].mem > 0"
```

`/api/4/status` answers even when glances is collecting nothing, and the root is a single page app, so the check asserts collected memory.
