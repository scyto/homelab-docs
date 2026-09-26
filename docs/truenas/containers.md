---
title: "Containers"
---

# containers

TrueNAS containers are not the same thing as [apps](apps.md). an app is a
docker compose project. a container here is a full system container with its
own init, distro userland and address on the LAN.

the one i run is pbs1, a Proxmox Backup Server. it lives here so the box holding
the backups does not depend on the proxmox cluster it is backing up. the PBS
side is in [backups](../backups/pbs-server.md).

## what the feature is, in 26.0

beta 26 replaced Incus with libvirt-lxc. containers are libvirt domains:

```
ps -o args -C libvirt_lxc
machinectl list
```

that shows the supervising `libvirt_lxc` process and the machine registered
with systemd. the API namespace changed to match. it is `container.*` now, not
`virt.*`:

```
midclt call container.query
midclt call container.get_instance <id>
```

anything written for 25.x uses a different namespace and backend.

## why a container and not an app

PBS runs several daemons, expects its own `/etc`, manages its own users and
wants a stable address other hosts connect to. that does not fit in a compose
file.

a system container gives it an init and a userland on the host's kernel, for a
fraction of a VM's overhead.

## how pbs1 is configured

| setting | value | why |
| --- | --- | --- |
| distro | Debian 13 | matches what PBS packages target |
| init | `/sbin/init` | a real init, so its services start normally |
| autostart | on | it must come back after a reboot without me |
| cpu | pinned to a cpuset | keeps backup verification off the cores everything else uses |
| idmap | isolated | root inside is an unprivileged uid on the host |
| security | no apparmor profile | the host loads apparmor, but pbs1 runs unconfined, so the idmap is what contains it |
| time | local | timestamps match the host's |

with the idmap, root in the container is not root on the NAS. a process that
breaks out lands as an unprivileged uid that owns nothing, and that is the main
reason i am comfortable running it.

## storage

the container's own storage and the backups are kept apart:

| what | where |
| --- | --- |
| the container's own root filesystem | `<pool>/.truenas_containers/containers/pbs1` |
| the datastore PBS writes backups into | `rust/local-backups/pbs`, passed in as `/mnt/pbs` |

- the root filesystem lives on the fast pool and is small, under a gigabyte. it
  holds a debian userland and PBS's configuration in `/etc/proxmox-backup`
- **the datastore is a dataset i made on the big pool**, passed through as a
  filesystem device. the backups are not inside the container's storage, so
  destroying and rebuilding the container does not touch them

```
midclt call container.device.query '[["container","=",<id>]]'
```

## networking

pbs1 has a VIRTIO NIC attached to the physical interface with its own MAC
address, and a static address, `192.168.1.80`, which its name resolves to. it
appears on the LAN as its own host, not behind a NAT or a port mapping on the
NAS.

- ifupdown2 owns the interface. installing PBS pulls it in, and PBS's network
  settings edit `/etc/network/interfaces`
- the debian image also runs systemd-networkd with DHCP on the same interface.
  left on, it adds a second address from DHCP, so it is turned off
- with networkd off, systemd-resolved gets its DNS servers from its own config.
  the `dns-nameservers` lines in `/etc/network/interfaces` do nothing without
  the `resolvconf` package

that matters for a backup server:

- proxmox hosts connect to it by its own name and address
- its certificate is issued for that name
- it is reachable when the NAS's own web UI is busy or restarting

## building pbs1

the container is made through the TrueNAS API, from a root shell on the NAS
(`sudo -i`), and PBS is then installed inside it. these steps are a first
build. replacing the container around the backups it already has is
[rebuilding pbs1](#rebuilding-pbs1), below.

### on the NAS

1. make the dataset the backups go in:

    ```
    midclt call pool.dataset.create '{"name": "rust/local-backups/pbs"}'
    ```

2. find the newest debian 13 image:

    ```
    midclt call container.image.query_registry | jq -r '.[] | select(.name == "debian:trixie:amd64:default") | .versions[].version'
    ```

    - PBS 4's packages are built for debian 13, trixie
    - a version is the image's build time, such as `20260924_05:24`

3. create the container with [the settings above](#how-pbs1-is-configured):

    ```
    midclt call -j container.create '{
      "name": "pbs1",
      "description": "proxmox backup server",
      "pool": "fast",
      "image": {"name": "debian:trixie:amd64:default", "version": "<version>"},
      "cpuset": "4",
      "idmap": {"type": "ISOLATED", "slice": 1},
      "shutdown_timeout": 30
    }'
    midclt call container.query '[["name","=","pbs1"]]' | jq '.[0].id'
    ```

    - autostart, `/sbin/init` and local time are the defaults, so they are not
      in the call
    - the name is also the hostname. TrueNAS writes it to `/etc/hostname` every
      time the container starts
    - slice 1 maps the container's uids to 2147065537 and up on the NAS, which
      is 2147000001 plus 65536 times the slice
    - `shutdown_timeout` is how long TrueNAS waits for a clean stop before it
      kills the container. the default is 90 seconds
    - the last line prints the container's id, which the next steps use as
      `<id>`

4. attach the dataset and a network interface:

    ```
    midclt call container.device.create '{"container": <id>, "attributes": {"dtype": "FILESYSTEM", "source": "/mnt/rust/local-backups/pbs", "target": "/mnt/pbs"}}'
    midclt call container.device.create '{"container": <id>, "attributes": {"dtype": "NIC", "type": "VIRTIO", "nic_attach": "enp195s0f1np1", "trust_guest_rx_filters": true}}'
    ```

    - the source has to be inside a pool. TrueNAS refuses any other path
    - `enp195s0f1np1` is the NAS's LAN port. attached to a port rather than a
      bridge, the NIC is a macvlan interface with its own MAC.
      `midclt call container.device.nic_attach_choices` lists both kinds
    - with macvlan the NAS and pbs1 cannot reach each other over the network,
      because a port passes no traffic between itself and its own macvlan
      interfaces. from the NAS, use `nsenter` as below
    - without `mac`, TrueNAS generates one

5. give the dataset to PBS's `backup` user. that is uid 34 in the container,
   and 2147065571 on the NAS with slice 1:

    ```
    chown -R 2147065571:2147065571 /mnt/rust/local-backups/pbs
    ```

    - this has to run on the NAS. inside the container a file owned by a uid
      outside its range shows as `nobody`, and root there cannot change it
    - `-R` matters for a datastore that came from another container or host,
      where every chunk still has the old owner. on a new dataset there is one
      directory to change

6. start it:

    ```
    midclt call container.start <id>
    midclt call container.query '[["name","=","pbs1"]]' | jq '.[0].status'
    ```

    the state should be `RUNNING`. `pid` is the container's init, which the
    next part uses.

### inside the container

1. open a shell in the container, from the NAS:

    ```
    nsenter -t <pid> -a -- bash -l
    ```

    - `<pid>` is the `pid` from the last step on the NAS
    - `-a` joins every namespace of the container, so you are root inside pbs1,
      with its files, network and uids

2. set the time zone:

    ```
    timedatectl set-timezone America/Los_Angeles
    ```

    - the image comes on UTC, and PBS runs its schedules in the server's time
      zone. without this, garbage collection at 02:00 runs at 02:00 UTC

3. add Proxmox's key and check it:

    ```
    apt update
    apt install -y wget nano
    wget https://enterprise.proxmox.com/debian/proxmox-archive-keyring-trixie.gpg -O /usr/share/keyrings/proxmox-archive-keyring.gpg
    sha256sum /usr/share/keyrings/proxmox-archive-keyring.gpg
    ```

    - the image has neither `wget` nor `nano`
    - the sum should be the one Proxmox publishes,
      `136673be77aba35dcce385b28737689ad64fd785a797e57897589aed08db6e45`. once
      the `proxmox-archive-keyring` package is installed it manages this file,
      and the sum may change with it

4. add the no-subscription repository, which is the one i use:

    ```debcontrol title="/etc/apt/sources.list.d/proxmox.sources"
    Types: deb
    URIs: http://download.proxmox.com/debian/pbs
    Suites: trixie
    Components: pbs-no-subscription
    Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
    ```

    - `Signed-By` has to name the key file from step 3

5. install PBS, then turn off the enterprise repository the package adds:

    ```
    apt update
    apt install -y proxmox-backup-server
    echo 'Enabled: false' >> /etc/apt/sources.list.d/pbs-enterprise.sources
    ```

    - `proxmox-backup-server` keeps debian's kernel. `proxmox-backup` would add
      the Proxmox kernel, which a container never boots
    - the enterprise repository needs a subscription. while it is on, PBS's
      daily package update fails on it with `401 Unauthorized` and ends with a
      warning

6. give it a static address, and turn off the image's DHCP. set the address in
   `/etc/network/interfaces`:

    ```text title="/etc/network/interfaces"
    auto lo
    iface lo inet loopback

    auto eth0
    iface eth0 inet static
        address 192.168.1.80/24
        gateway 192.168.1.1
        mtu 9000

    iface eth0 inet6 static
        address 2001:db8:1000:1::80/64
        gateway 2001:db8:1000:1::1
    ```

    then point systemd-resolved at the AdGuards, turn off systemd-networkd, and
    apply the file:

    ```
    mkdir -p /etc/systemd/resolved.conf.d
    printf '[Resolve]\nDNS=192.168.1.5 192.168.1.6\nDomains=mydomain.com\n' > /etc/systemd/resolved.conf.d/lan.conf
    systemctl restart systemd-resolved
    systemctl disable --now systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service
    mv /etc/systemd/network/eth0.network /etc/systemd/network/eth0.network.disabled
    ifreload -a
    ip -br addr show eth0
    ```

    - `2001:db8::` is the documentation prefix. use your own
    - DNS comes first. with networkd off, resolved has no servers until its own
      config names some
    - renaming `eth0.network` keeps DHCP off if networkd is ever turned back on
    - the last line should show the static addresses and a link-local one, and
      nothing from DHCP
    - this is done from the NAS's `nsenter` shell, so a mistake here doesn't cut
      you off

7. give root a password:

    ```
    passwd
    ```

    - the image's root has none. PBS's web UI logs in as `root@pam`, and so
      does the proxmox [VM backup storage](../backups/vm-backups-pbs.md#1-the-pbs-storage),
      which keeps its copy of this password in
      `/etc/pve/priv/storage/pbs1-vms.pw`
    - `@pam` means the container's own `/etc/shadow`, not PBS's configuration

8. create the datastore:

    ```
    proxmox-backup-manager datastore create mnt-pbs /mnt/pbs --gc-schedule 02:00
    ```

    - on a rebuild add `--reuse-datastore true`. without it PBS refuses a
      directory that has files in it, with `datastore path not empty`
    - keep the name `mnt-pbs`. every client's repository names it
    - users, tokens, ACLs and the prune and verify jobs live in the container's
      `/etc/proxmox-backup`, not in the datastore. set them up as in
      [backups](../backups/pbs-server.md)

9. get the certificate. it comes from Let's Encrypt over a DNS challenge
   through Cloudflare, so pbs1 does not have to be reachable from the internet.
   first put the Cloudflare API token in a file, as one line,
   `CF_Token=<token>`:

    ```
    install -m 600 /dev/null /root/cf.env
    nano /root/cf.env
    ```

    then register, add the plugin and order:

    ```
    proxmox-backup-manager acme account register <account> <email>
    proxmox-backup-manager acme plugin add dns 1 --api cf --data /root/cf.env
    rm /root/cf.env
    proxmox-backup-manager node update --acme account=<account>
    proxmox-backup-manager node update --acmedomain0 pbs1.mydomain.com,plugin=1
    proxmox-backup-manager acme cert order
    ```

    - the token needs Cloudflare's DNS edit permission on the zone
    - `register` asks for a directory, and `0` is Let's Encrypt's production
      one. then it asks you to accept their terms
    - `cf` is acme.sh's Cloudflare plugin, and `1` is the id i gave the plugin
      in PBS. `plugin=1` makes the domain use it
    - PBS keeps its own copy of the token in
      `/etc/proxmox-backup/acme/plugins.cfg`, readable by root only, so the
      file can go
    - PBS renews the certificate itself. its daily update job orders a new one
      once the current one is within 30 days of expiring

10. check it:

    ```
    proxmox-backup-manager datastore list
    proxmox-backup-manager cert info
    ```

    the datastore shows as `mnt-pbs` on `/mnt/pbs`, and the certificate's
    issuer is Let's Encrypt. clients connect by name, so `pbs1.mydomain.com`
    needs a DNS record pointing at pbs1. the web UI is then on
    `https://pbs1.mydomain.com:8007`.

    those checks don't cover logins, permissions or writes. once the users,
    tokens and ACLs from [backups](../backups/pbs-server.md) exist, check both
    kinds of login before relying on it. on a proxmox node, the VM storage
    logs in as `root@pam` and should show `active`:

    ```
    pvesm status --storage pbs1-vms
    ```

    then run one token client's backup, such as the
    [cephFS backup](../backups/cephfs.md).

### rebuilding pbs1

i have not rebuilt pbs1. this is what the container holds that a rebuild has to
bring across, and how. deleting the container deletes its root filesystem, and
the datastore on its own dataset is all that survives.

1. from the NAS, while the old container runs, save its configuration and note
   its MAC:

    ```
    pid=$(midclt call container.query '[["name","=","pbs1"]]' | jq -r '.[0].status.pid')
    nsenter -t "$pid" -a -- tar -C / -czf - etc/proxmox-backup etc/network/interfaces > /root/pbs1-config.tgz
    chmod 600 /root/pbs1-config.tgz
    midclt call container.device.query '[["container","=",<old id>]]' | jq -r '.[] | select(.attributes.dtype == "NIC") | .attributes.mac'
    ```

    - **the archive holds the API token secrets, the certificate's key and the
      Cloudflare token.** keep it root only and delete it once pbs1 is back
    - `/etc/proxmox-backup` holds the users, the token secrets, the ACLs, the
      prune and verify jobs, the datastore's definition, the certificate and
      the ACME setup. new tokens would have new secrets, and every client's
      token file would stop working
    - `/etc/network/interfaces` holds pbs1's static addresses, which its name
      resolves to. the MAC isn't what gives it an address, but keeping it means
      the router and the switches still see the same client
    - the new container needs the name pbs1, so the old one has to be deleted
      before it is made, and its MAC goes with it

2. delete the old container, then follow [on the NAS](#on-the-nas) steps 2, 3,
   4 and 6, with two changes:

    - use the same idmap slice. the datastore's files already belong to that
      slice's `backup` uid, so step 5's chown is skipped. it walks every chunk,
      over a terabyte here, and is only needed if the slice changes
    - add the old MAC to the NIC in step 4: `"mac": "<old mac>"`

3. inside the new container, follow [inside the container](#inside-the-container)
   steps 1 to 7, to install PBS, set up its network and set root's password.
   then restore the configuration from the NAS instead of steps 8 and 9:

    ```
    pid=$(midclt call container.query '[["name","=","pbs1"]]' | jq -r '.[0].status.pid')
    nsenter -t "$pid" -a -- tar -C / -xzf - < /root/pbs1-config.tgz
    nsenter -t "$pid" -a -- systemctl restart networking proxmox-backup proxmox-backup-proxy
    ```

    - the archive already defines the datastore, so it is not created again
    - `root@pam`'s password is not in `/etc/proxmox-backup` but in the
      container's `/etc/shadow`, so step 7 has to set it to the one the proxmox
      PBS storage already uses, or that storage stops authenticating

4. check it the same way as step 10, including `pvesm status` and one client
   backup, then delete `/root/pbs1-config.tgz`

## what i would check after an upgrade

containers are the newest part of this release, and their backend changed in
it. list them:

```
midclt call container.query | python3 -m json.tool | grep -E '"name"|"state"'
```

confirm it is `RUNNING` and that autostart survived. then check that PBS itself
answers: the container can be running while the datastore is not.
