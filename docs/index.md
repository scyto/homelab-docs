---
title: "Home"
---

# scyto's homelab docs

Build notes for two connected projects, a **3-node Proxmox cluster** meshed over
Thunderbolt with Ceph on top and the **Docker Swarm** that runs on it, plus the
**TrueNAS** box and the **backups** that keep copies of both off the cluster.

!!! note "A word of warning"

    These are designed to be primarily a re-install guide for myself (writing
    things down helps me memorize the knowledge), so don't take any of this on
    blind faith. Some areas are well tested and the docs are robust, some items
    less so. YMMV.

<div class="grid cards" markdown>

-   :material-server-network:{ .lg .middle } **[Proxmox Cluster](proxmox/index.md)**

    ---

    Soup-to-nutz: hardware, base install, Thunderbolt mesh networking with
    Openfabric routing, Ceph and high availability, CephFS storage, and
    migrating a fleet of VMs off Hyper-V.

-   :material-docker:{ .lg .middle } **[Docker Swarm](docker-swarm/index.md)**

    ---

    A 3-node Debian swarm with Portainer, KeepaliveD, VirtioFS-backed shared
    storage, stacks in git, and templates for everything I run on it.

-   :material-nas:{ .lg .middle } **[TrueNAS](truenas/index.md)**

    ---

    The NAS outside the cluster: Proxmox Backup Server as a container, S3 with
    Versity Gateway, and the app gotchas that cost me time.

-   :material-raspberry-pi:{ .lg .middle } **[Raspberry Pi](raspberry-pi/index.md)**

    ---

    The Pi that holds the home automation radios: Docker, the stacks, a GPS
    time source with PPS, and a PoE HAT OLED.

-   :material-access-point-network:{ .lg .middle } **[Thread](thread/index.md)**

    ---

    One Thread network owned by Home Assistant, two border routers (the add-on
    over ser2net and an ESP32 board), and getting the add-on back after the Pi
    has been off.

-   :material-backup-restore:{ .lg .middle } **[Backups](backups/index.md)**

    ---

    What gets backed up, how, and where it lands: VMs and CephFS to PBS,
    Portainer to S3, and the databases that need more than a file copy.

</div>

## Where this came from

These pages started life as a collection of GitHub gists and were consolidated
into this repo. Every page records the gist it came from in its `source_gist`
front matter, and the original gists remain in place, **including their comment
threads**, which are worth reading. Several are long-running troubleshooting
discussions with far more collective experience in them than I have on my own.

The two busiest, with hundreds of comments between them:

- [Thunderbolt Networking Setup](https://gist.github.com/scyto/67fdc9a517faefa68f730f82d7fa3570)
- [vGPU Passthrough](https://gist.github.com/scyto/e4e3de35ee23fdb4ae5d5a3b85c16ed3)

## Questions and troubleshooting

The busiest pages have a comment box at the bottom, backed by
[GitHub Discussions](https://github.com/scyto/homelab-docs/discussions). Replies
thread properly, answers can be marked, and everything is searchable, none of
which gist comments could do.

Anything not covered by a specific page belongs in
[Q&A](https://github.com/scyto/homelab-docs/discussions/categories/q-a).

## Contributing

Found a typo, a broken command, or something that's gone stale? There's an
:material-pencil: edit icon at the top of every page, corrections via pull
request are very welcome.
