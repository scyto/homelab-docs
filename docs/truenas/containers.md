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
| security | apparmor | libvirt confines it by default |
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
  is a debian userland, and nothing i care about is in it
- **the datastore is a dataset i made on the big pool**, passed through as a
  filesystem device. the backups are not inside the container's storage, so
  destroying and rebuilding the container does not touch them

```
midclt call container.device.query '[["container","=",<id>]]'
```

## networking

pbs1 has a VIRTIO NIC attached to the physical interface with its own MAC
address. it gets its own DHCP lease and appears on the LAN as its own host, not
behind a NAT or a port mapping on the NAS.

that matters for a backup server:

- proxmox hosts connect to it by its own name and address
- its certificate is issued for that name
- it is reachable when the NAS's own web UI is busy or restarting

## what i would check after an upgrade

containers are the newest part of this release, and their backend changed in
it. list them:

```
midclt call container.query | python3 -m json.tool | grep -E '"name"|"state"'
```

confirm it is `RUNNING` and that autostart survived. then check that PBS itself
answers: the container can be running while the datastore is not.
