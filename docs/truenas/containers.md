---
title: "Containers"
---

# containers

TrueNAS containers are **not** the same thing as [apps](apps.md). an app is a
docker compose project; a container here is a full system container with its
own init, its own distro userland and its own address on the LAN.

i run one: **pbs1**, a Proxmox Backup Server, so the box holding the backups
does not depend on the proxmox cluster it is backing up. see
[backups](../backups/pbs-server.md) for the PBS side.

## what the feature is, in 26.0

beta 26 **replaced Incus** with libvirt-lxc. containers are libvirt domains:

```
ps -o args -C libvirt_lxc
machinectl list
```

that shows the supervising `libvirt_lxc` process and the machine registered
with systemd. the API namespace changed to match — it is `container.*` now, not
`virt.*`:

```
midclt call container.query
midclt call container.get_instance <id>
```

worth knowing if you are following anything written for 25.x, where the
namespace and the backend were both different.

## why a container and not an app

PBS wants to be a machine. it runs several daemons, expects its own
`/etc`, manages its own users and wants a stable address other hosts connect
to. wrapping that in a compose file fights it the whole way.

a system container gives it an init and a userland, at a fraction of a VM's
overhead, on the same kernel.

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

**the idmap is the part worth understanding.** root in the container is not
root on the NAS. a process that breaks out lands as an unprivileged uid that
owns nothing, which is the main reason this is comfortable to run at all.

## storage

two different things, deliberately kept apart:

| what | where |
| --- | --- |
| the container's own root filesystem | `<pool>/.truenas_containers/containers/pbs1` |
| the datastore PBS writes backups into | `rust/local-backups/pbs`, passed in as `/mnt/pbs` |

- the root filesystem lives on the **fast** pool and is small — under a
  gigabyte. it is a debian userland, and nothing i care about is in it
- **the datastore is a dataset i made on the big pool**, passed through as a
  filesystem device. so the backups are not inside the container's storage, and
  destroying and rebuilding the container does not touch them
- that separation is the point. a container i can throw away, holding a pointer
  to data i cannot

```
midclt call container.device.query '[["container","=",<id>]]'
```

## networking

a VIRTIO NIC attached to the physical interface with its **own MAC address**,
so it gets its own DHCP lease and appears on the LAN as its own host — not
behind a NAT or a port mapping on the NAS.

that matters for a backup server:

- proxmox hosts connect to it by its own name and address
- its certificate is issued for that name
- it is reachable when the NAS's own web UI is busy or restarting

## what i would check after an upgrade

containers are the newest part of this release and the backend changed in it,
so:

```
midclt call container.query | python3 -m json.tool | grep -E '"name"|"state"'
```

confirm it is `RUNNING` and that autostart survived, then check PBS itself
answers — a running container is not a running datastore.
