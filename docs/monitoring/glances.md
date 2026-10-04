---
title: "Glances"
---

# glances on every host

i run [glances](https://github.com/nicolargo/glances) on all nine hosts: in a container on the six docker hosts, and on the host itself on the three proxmox nodes. every one runs 4.5.6 on port `61208`, so the [dashboard](homepage.md)'s tiles and the [gatus](gatus.md) checks have one shape for all of them. clicking a tile opens that host's glances.

--8<-- "blocks/swarm/glances/compose.yml.md"

## before you deploy

1. on each swarm node, syn02 and pi-zwave01, create the empty directory for the root filesystem's probe:

    ```
    sudo mkdir -p /var/lib/glances-probe
    ```

    - a missing directory fails the task on the swarm, and keeps the container from starting on a standalone host
    - it stays empty. glances reads only the size of the filesystem it sits on

2. on one swarm node, create the cephfs probe's directory, which all three nodes share:

    ```
    sudo mkdir -p /mnt/docker-cephFS/.glances-probe
    ```

3. on syn02, create the volume1 probe's directory:

    ```
    sudo mkdir -p /volume1/docker/glances-probe
    ```

    - truenas1 binds no probes, so it needs none of these

## state considerations

on the swarm it keeps nothing, and there are no volumes. it binds the host's `/etc/os-release` and the two empty probe directories read-only, and edits its three settings into the image's own config at every start.

## network considerations

- on the swarm it joins docker's built-in `host` network and publishes no port, so `61208` is on each node's own address. it joins no overlay network. the standalone hosts use `network_mode: host`, and [the proxmox nodes](#on-the-proxmox-nodes) listen on the node's lan address
- reach each host at its own address, `192.168.1.41:61208` for docker01, or by name through [traefik](../apps/traefik.md), `https://glances-docker01.mydomain.com`. never use the keepalived VIP, which moves between nodes

## placement considerations

on the swarm it runs `mode: global`, one task per node, each on that node's own address, so each tile names the host it reports.

## on the docker hosts

in a container glances reports the container's network interfaces, OS name and mounts. four changes make it report the host's.

**host networking** lets it see the host's real interfaces and report the host's hostname. on the swarm that's the built-in `host` network, attached as an external network. on a standalone host it's `network_mode: host`.

```yaml title="swarm/glances/compose.yml"
services:
  glances:
    networks:
      - hostnet
networks:
  hostnet:
    external: true
    name: host
```

**the host's `/etc/os-release`** is bound read-only. without it glances reports the image's alpine. syn02 has none, and its file below builds one.

**an empty directory per filesystem** is bound read-only under `/host/`. glances lists the container's own mounts, and an empty directory reports the filesystem it lives on. the swarm nodes bind one from the root filesystem and one from cephfs:

```yaml title="swarm/glances/compose.yml"
      - type: bind
        source: /var/lib/glances-probe
        target: /host/root
        read_only: true
      - type: bind
        source: /mnt/docker-cephFS/.glances-probe
        target: /host/cephfs
        read_only: true
```

syn02 binds root and `/volume1`, pi-zwave01 root only, and truenas1 none.

**three settings** are edited into the image's own config at start on every host: hide docker's veths and bridges, show only the `/host/` probes, and allow `virtiofs`. cephfs reaches the VMs over virtiofs, and glances hides it by default. the swarm's copy also writes a small launcher and starts glances through it, for the process list below:

```yaml title="swarm/glances/compose.yml"
    entrypoint:
      - /bin/sh
      - -c
      - |
        set -e
        /venv/bin/python3 - <<'PY'
        import configparser
        c = configparser.ConfigParser(interpolation=None)
        c.read("/etc/glances/glances.conf")
        c["network"]["hide"] = "veth.*,docker.*,br-.*,lo"
        c["fs"]["show"] = "/host/.*"
        c["fs"]["allow"] = "virtiofs"
        c.write(open("/tmp/glances.conf", "w"))
        PY
        cat > /tmp/glances-host.py <<'PY'
        # Glances on the host's processes, through the host's /proc (header).
        import runpy, sys, psutil
        # As `python -m` would: the working directory first on the path. The
        # image keeps glances in /app, its WORKDIR; a script would put /tmp.
        sys.path.insert(0, "")
        from psutil import _pslinux
        psutil.PROCFS_PATH = "/host/proc"
        # nice from /proc/<pid>/stat (field 19), not getpriority(): the
        # syscall resolves the pid in this container's namespace.
        def nice_get(self):
            with open(f"{self._procfs_path}/{self.pid}/stat", "rb") as f:
                return int(f.read().rsplit(b")", 1)[1].split()[16])
        _pslinux.Process.nice_get = _pslinux.wrap_exceptions(nice_get)
        runpy.run_module("glances", run_name="__main__", alter_sys=True)
        PY
        exec /venv/bin/python$${PYTHON_VERSION} /tmp/glances-host.py -C /tmp/glances.conf $${GLANCES_OPT}
```

- configparser reads `/etc/glances/glances.conf`, keeps every other default, and writes the result to `/tmp/glances.conf`, which `-C` hands to glances. `/etc/glances` belongs to root and the container runs as nobody. `set -e` stops the container if the edit fails
- it runs as `65534:65534` with every capability dropped. nothing it reads needs root, and on the standalone hosts it shares the host's pid namespace, where root could signal any host process; these pages have no login. syn02 gets there differently: its wrapper writes `/etc/os-release`, which needs root, so it starts as root with only `SETUID` and `SETGID`, writes the file, and drops to 65534 in python before glances starts. it also sets `LOGNAME=nobody`, because DSM's `/etc/passwd` has no uid 65534 and glances needs a user name to start
- every host edits its config in the entrypoint like this, because a standalone host can't mount a config file from the stack: a relative bind resolves inside portainer's git clone, not on the host.
- `$$` is compose's escape for `$`, so the shell expands `GLANCES_OPT` and compose leaves it alone
- it has no docker socket, so it shows no container list. [dozzle](dozzle.md) and portainer cover containers
- the process list is the host's. a swarm service can't use `pid: host`, so on the swarm:
    - the host's `/proc` is bound read-only at `/host/proc`, and the host's `/etc/passwd` for user names
    - a launcher, `/tmp/glances-host.py`, points psutil at `/host/proc` and runs glances as `python -m glances` would
    - the launcher reads `nice` from `/proc/<pid>/stat`. psutil's `nice` is a `getpriority()` call, which the kernel resolves in the container's own pid namespace, so it fails for every host process
- the container keeps its own pid namespace: it reads the host's process files but can't signal a host process
- gatus checks the process count on each node. a glances update that reads another attribute by system call would shrink the list to a few rows and leave every other number right

## on the standalone hosts

truenas1, syn02 and pi-zwave01 are not in the swarm, so each runs the container as a stack of its own. four things differ from the swarm's file:

- `network_mode: host`, in place of the `host` network
- `pid: host`, `no-new-privileges`, and the host's `/etc/passwd` read-only: the host's process list, with its user names. a swarm service takes neither option. a uid the host's file doesn't name shows as a number
- each bind is the long form with `create_host_path: false`, so a missing source keeps the container from starting. with the short form, docker would create a directory in its place, even at `/etc/os-release`
- a healthcheck, which asserts collected memory as [gatus](gatus.md) does. docker never acts on a standalone container's health, so it only reports it. the swarm's file has none: swarm replaces an unhealthy task, so a failing check there would restart glances

on truenas1 it is a stack, not the ix-glances catalog app, because the app has no way to bind the host's `/etc/os-release` and serves on port 30015.

--8<-- "blocks/truenas1/glances/compose.yml.md"

--8<-- "blocks/syn02/glances/compose.yml.md"

--8<-- "blocks/pi-zwave01/glances/compose.yml.md"

## on the proxmox nodes

glances runs on the host as a systemd service, in a python venv pinned to 4.5.6.

- not in an LXC. proxmox gives every container LXCFS, so `/proc` shows the container's allowance, not the node's. an LXC also has its own network namespace and root filesystem, so glances would report the LXC
- not from debian's `glances` package. debian strips the prebuilt web UI, because it can't be rebuilt from source with debian's own tools, and has marked the bug won't-fix. without the UI there's no page for the tile to open

it needs three files:

<!-- fragment: illustrative -->

```ini title="/etc/glances/glances.conf"
[network]
hide=lo,tap.*,fwbr.*,fwpr.*,fwln.*,veth.*

[fs]
hide=/boot.*,/var/lib/glances,/var/tmp
```

- the hidden interfaces are proxmox's per-guest `tap` and firewall bridges. the hidden filesystems are the service sandbox's own mounts

<!-- fragment: illustrative -->

```sh title="/etc/default/glances"
GLANCES_BIND=192.168.1.81
```

use each node's own address in `GLANCES_BIND`.

<!-- fragment: illustrative -->

```ini title="/etc/systemd/system/glances.service"
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
```

- it listens on the node's lan address only, runs as its own user with no capabilities, and can write only its state directory and a private `/tmp`

then run these as root on each node:

1. install python's venv module:

    ```
    apt-get update
    apt-get install --yes python3-venv
    ```

2. create the `glances` user:

    ```
    useradd --system --home-dir /var/lib/glances --no-create-home --shell /usr/sbin/nologin glances
    ```

3. create the venv and install glances in it:

    ```
    python3 -m venv /opt/glances
    /opt/glances/bin/pip install --disable-pip-version-check 'glances[web]==4.5.6'
    ```

    - after a proxmox major upgrade, which brings a new python, rebuild the venv: delete `/opt/glances` and run the `venv` and `pip` lines again

4. create `/etc/glances`, then write the three files above:

    ```
    mkdir --parents /etc/glances
    ```

5. start the service:

    ```
    systemctl daemon-reload
    systemctl enable --now glances.service
    ```

6. check it answers:

    ```
    sleep 5
    curl --silent http://$(sed -n 's/^GLANCES_BIND=//p' /etc/default/glances):61208/api/4/quicklook/mem; echo
    ```

    - the last line must print a memory figure above zero. `systemctl status` straight after starting reads active even when the bind is about to fail

## checking it

every host should answer with the share of its memory in use:

```
for ip in 192.168.1.41 192.168.1.42 192.168.1.43 192.168.1.86 192.168.1.31 192.168.1.96 192.168.1.81 192.168.1.82 192.168.1.83; do
  printf '%s ' "$ip"; curl -s "http://$ip:61208/api/4/quicklook/mem"; echo
done
```

```text
192.168.1.41 {"mem": 41.8}
192.168.1.42 {"mem": 19.0}
192.168.1.43 {"mem": 37.9}
192.168.1.86 {"mem": 15.6}
192.168.1.31 {"mem": 8.8}
192.168.1.96 {"mem": 7.3}
192.168.1.81 {"mem": 36.9}
192.168.1.82 {"mem": 24.5}
192.168.1.83 {"mem": 39.3}
```

a figure above zero means glances is collecting. `/api/4/status` and the web page both answer when it is collecting nothing, so [gatus](gatus.md) asserts the same figure on every host:

```yaml title="gatus/config/20-proxmox.yaml"
    url: "http://192.168.1.81:61208/api/4/quicklook"
    conditions:
      - "[STATUS] == 200"
      - "[BODY].mem > 0"
```

the disks a docker host reports should be its probes and nothing else:

```
curl -s http://192.168.1.41:61208/api/4/fs | jq -r '.[].mnt_point'
```

```text
/host/root
/host/cephfs
```
