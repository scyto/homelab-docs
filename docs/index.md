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

    These docs are also undergoing major changes right now: pages are moving,
    being rewritten and being filled in. Expect gaps, and be careful before
    relying on anything here.

    Yes i used AI to help me port these from the gists and update them.  This is 
    the only way i can scale. I will continue to review for 'odd AI wording' and accuracy. 

<div class="grid cards" markdown>

-   :material-server-network:{ .lg .middle } **[Proxmox Cluster](proxmox/index.md)**

    ---

    Soup-to-nutz: hardware, base install, Thunderbolt mesh networking with
    Openfabric routing, Ceph and high availability, CephFS storage, and
    migrating a fleet of VMs off Hyper-V.

-   :material-docker:{ .lg .middle } **[Docker](docker/index.md)**

    ---

    A 3-node Debian swarm with KeepaliveD and VirtioFS-backed shared storage,
    three standalone Docker hosts, one Portainer over all of them, stacks in
    git, and the conventions every stack follows.

-   :material-apps:{ .lg .middle } **[Apps](apps/index.md)**

    ---

    Details on the apps i have running including app configuration and compose/stack files when on docker, for example: AdGuard DNS, NPM as reverse proxy, auth, certificates, the arr stack, Frigate, etc.

-   :material-monitor-dashboard:{ .lg .middle } **[Monitoring](monitoring/index.md)**

    ---

    Monitoring: Gatus checks, Glances on every host, Dozzle for logs, and a Homepage dashboard that pulls it together. This will expand to include both prometheus and other centralized logging, grafana dashboards and notifications. 

-   :material-key-variant:{ .lg .middle } **[Secrets](secrets/index.md)**

    ---

    An experimental encrypted store for keeping credentials out of git. Most
    people should just use Docker secrets, or set env vars by hand.

-   :material-nas:{ .lg .middle } **[TrueNAS](truenas/index.md)**

    ---

    TrueNAS: This augments the Proxmox cluster and is used for traditional NAS storage and VMs & containers that need the unique hardware.  Section covers ZFS pools and data sets, system extensions for GPU and AI accelerators, Proxmox Backup Server as a container, S3 with Versity Gateway.

-   :material-raspberry-pi:{ .lg .middle } **[Raspberry Pi](raspberry-pi/index.md)**

    ---

    The Pi that holds the home automation radios (zigbee, zwave and thread): Uses docker to deploy apps on the pi. Also includes a GPS time source with PPS, and a PoE HAT OLED.

-   :material-access-point-network:{ .lg .middle } **[Thread](thread/index.md)**

    ---

    Thread network owned by Home Assistant, two border routers RCP for redundancy.  1 x OTBR using HAOS and ser2net on the pi.  Another RCP / OTBR on an ESP32+Thread dev board.

-   :material-backup-restore:{ .lg .middle } **[Backups](backups/index.md)**

    ---

    What gets backed up, how, and where it lands: VMs, CephFS and the Pi to
    PBS, PBS copied on to Azure, Portainer to S3, and a plan for the databases
    that need more than a file copy.

</div>

## Where this came from

These pages started life as a collection of GitHub gists and were consolidated
into this repo. Each of those pages links its gist at the bottom, and the
original gists remain in place, **including their comment threads**, which are worth reading. Several are long-running troubleshooting
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
