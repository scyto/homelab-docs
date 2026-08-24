# homelab-docs

My homelab build notes, published at **<https://scyto.github.io/homelab-docs/>**.

Two projects live here:

- **[Proxmox Cluster](docs/proxmox/index.md)** — 3× Intel NUC 13, Thunderbolt
  mesh networking with Openfabric routing, Ceph, HA, and Hyper-V migrations.
- **[Docker Swarm](docs/docker-swarm/index.md)** — 3-node Debian swarm with
  Portainer, KeepaliveD, VirtioFS/CephFS shared storage, and stack templates.

These are primarily re-install notes for myself. Don't take any of it on blind
faith — some parts are well tested, some much less so.

## History

This content was consolidated from ~47 GitHub gists. The originals are still
live and each page links back to its source via `source_gist` front matter. The
gist comment threads were **not** migrated (GitHub has no API for that) and are
worth reading — some run to hundreds of replies of community troubleshooting.

## Building locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

Then open <http://127.0.0.1:8000>.

## Contributing

Typo fixes and corrections are welcome — use the edit icon on any page, or open
a PR directly. CI builds the site with `--strict`, so a broken internal link
will fail the build.
