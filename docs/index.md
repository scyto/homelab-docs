---
title: "Home"
---

# scyto's homelab docs

Build notes for two connected projects: a **3-node Proxmox cluster** meshed over
Thunderbolt with Ceph on top, and the **Docker Swarm** that runs on it.

!!! note "A word of warning"

    These are designed to be primarily a re-install guide for myself — writing
    things down helps me memorize the knowledge. As such, don't take any of this
    on blind faith. Some areas are well tested and the docs are robust; some
    items, less so. YMMV.

<div class="grid cards" markdown>

-   ### :material-server-network: [Proxmox Cluster](proxmox/index.md)

    Soup-to-nutz: hardware, base install, Thunderbolt mesh networking with
    Openfabric routing, Ceph and high availability, CephFS storage, and
    migrating a fleet of VMs off Hyper-V.

-   ### :material-docker: [Docker Swarm](docker-swarm/index.md)

    A 3-node Debian swarm with Portainer, KeepaliveD, VirtioFS-backed shared
    storage, and stack templates for everything I run on it.

</div>

## Where this came from

These pages started life as a collection of GitHub gists and were consolidated
into this repo. Every page records the gist it came from in its `source_gist`
front matter, and the original gists remain in place — **including their comment
threads**, which are worth reading. Several of them are long-running
troubleshooting discussions with far more collective experience in them than I
have on my own.

Notably: [Thunderbolt Networking Setup](https://gist.github.com/scyto/67fdc9a517faefa68f730f82d7fa3570)
and [vGPU Passthrough](https://gist.github.com/scyto/e4e3de35ee23fdb4ae5d5a3b85c16ed3)
have accumulated hundreds of comments between them.

## Contributing

Found a typo, a broken command, or something that's gone stale? There's an
:material-pencil: edit icon at the top of every page — corrections via pull
request are very welcome.
