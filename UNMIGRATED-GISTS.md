# Unmigrated gists

The [homelab-docs](https://scyto.github.io/homelab-docs/) site was built from the 47 gists
reachable from the two hub gists (*my proxmox cluster* and *My Docker Swarm Architecture*).

These **16** gists were left out: nothing in that tree links to them, so they were never
part of the graph. This is a review list, not a backlog, several are probably fine as-is.

Tick a box once you have decided what to do with one.

## Candidates to migrate

Real, standalone content that nothing currently links to. Each would slot into the site with a bit of editing.

- [ ] **[CasaTunes → Music Assistant conversion](https://gist.github.com/scyto/2eef6306f3ac0e90252d21b35c0e6473)**
  `1-ct-converted-to-ma.md, 2-using-squeezelite.md, 3-docker-sendspin.md, 4-asound.conf, 5-operations-guide.md, 6-lr-channel-check-test-script.sh` · 23,221 bytes · 0 comments · updated 2026-05-31
  Four-part guide (squeezelite, docker sendspin, asound config). The largest unmigrated topic and arguably deserves its own section rather than folding into either existing one.

- [ ] **[TrueNAS VM prep — PCIe passthrough](https://gist.github.com/scyto/305224b5e651f6d3c318744bfde99974)**
  `passthrough-setup.md` · 8,609 bytes · 0 comments · updated 2026-05-14
  Reference snapshot of pve-nas1 PCIe layout. Fits naturally under Proxmox → Extra Credit.

- [ ] **[Home Assistant USBIP Z-Wave setup](https://gist.github.com/scyto/9be69eb8f1e736ae69a0fa70dc4a6ed2)**
  `001-README.md, 99-zwave-stick.rules, usbip.service, usbipManager.sh, usbipd.service` · 7,210 bytes · 0 comments · updated 2026-01-23
  Five files including systemd units and udev rules. Standalone; would need a home in the nav.

- [ ] **[Ceph IP migration (/128 → /64)](https://gist.github.com/scyto/64e79a694b286d3b70f8b3663d19eb76)**
  `ceph-ip-migration-on-proxmox.md` · 3,901 bytes · 2 comments · updated 2026-01-23
  Fits under Proxmox → Ceph. Your own summary is "DON'T, IT IS BAD EVERY TIME", still useful as a warning page.

- [ ] **[DHCP Option 119 generator script](https://gist.github.com/scyto/c7032bb1164d9af02fd12c29f4113a2b)**
  `dhcp_option119.py` · 1,319 bytes · 0 comments · updated 2025-01-18
  A single Python script. Might be better as a small repo or a snippet page than a doc.

- [ ] **[NAS Debian install](https://gist.github.com/scyto/bf8958d94e02cd9ed50e54c280f63167)**
  `nas-debian.md` · 1,581 bytes · 0 comments · updated 2025-11-22
  Very short (1.5 KB) and overlaps the existing Debian VM install page, possibly merge rather than add.

- [ ] **[Building a TrueNAS sysext with Claude Code](https://gist.github.com/scyto/80fde76f4043004120ed42c24cdc85a6)**
  `gistfile1.md` · 117,662 bytes · 0 comments · updated 2026-06-12
  An annotated session transcript, 117 KB, by far the biggest. Different genre from the rest of the site; may not belong here at all.

## Superseded, probably leave as archive

These are earlier iterations of guides already on the site. Worth keeping as gists for their history and comments, but migrating them would duplicate current content.

- [ ] **[IPv4 OSPF mesh for Ceph](https://gist.github.com/scyto/629c61d36af07b5ee45adfb172e25384)**
  `.ospf-mesh-net.md, dual-stack-ospf.md` · 8,557 bytes · 21 comments · updated 2024-12-27
  Marked deprecated in the gist itself, superseded by Openfabric. **21 comments**, the most of any orphan, so keep the gist alive regardless.

- [ ] **[Openfabric for Thunderbolt/Ceph (2023)](https://gist.github.com/scyto/fca5e3112822bc5a53d3b9048202e00c)**
  `openfabric-mesh-net.md` · 3,957 bytes · 0 comments · updated 2023-09-22
  Requires a custom-patched 6.5.2 kernel. Historical.

- [ ] **[FRR OpenFabric IPv6 initial setup (fc00::/128)](https://gist.github.com/scyto/bdd5381fe9170ec10009cddf8687446b)**
  `mesh-network.md` · 3,649 bytes · 1 comment · updated 2026-01-23
  Documents the original /128 design you later migrated away from.

- [ ] **[Thunderbolt mesh — staged guide (refactor1)](https://gist.github.com/scyto/a02bbcf947f4a18773c30fa3d12bf495)**
  `refactor1.md` · 5,730 bytes · 0 comments · updated 2026-01-23
  Reads as an AI-generated restructuring draft, not a tested guide.

- [ ] **[Thunderbolt mesh — FRR + BGP (refactor2)](https://gist.github.com/scyto/935b6d214ee6d87741fb5e9646e98161)**
  `refactor2.md` · 5,357 bytes · 1 comment · updated 2026-06-22
  Same, BGP variant. Note the site documents Openfabric, not BGP.

## Secret gists, decide separately

These are **secret**, not public. A secret gist is reachable by anyone who has its URL, so the URL is its only access control, printing it in this public repo would effectively publish it. Links are withheld for that reason; find them at <https://gist.github.com/scyto> while signed in.

- [ ] **k3s node prep notes: *secret, link withheld***
  `k3s-prep-notes.md` · 5,821 bytes · 3 comments · updated 2025-08-29
  Described by you as "secret notes". Review before any migration.

- [ ] **WordPress multisite on Docker: *secret, link withheld***
  `wordpress-multisite-docker.md` · 4,847 bytes · 0 comments · updated 2025-04-15
  Contains a real personal domain in the Cloudflare DNS steps, would need scrubbing first.

- [ ] **USBIP systemd units + script: *secret, link withheld***
  `usbip-client.service, usbip-server.service, usbip.sh` · 8,806 bytes · 0 comments · updated 2023-10-11
  Overlaps the public HA USBIP Z-Wave gist above; consider consolidating.

- [ ] **Thunderbolt kernel 6.5.2 patches: *secret, link withheld***
  `.tbkernel-fixes.md, 0001-thunderbolt-Restart-handshake-after-failure.patch, 0002-net-thunderbolt-Fix-TCP-UDPv6-checksum.patch` · 5,769 bytes · 0 comments · updated 2023-09-08
  The gist itself notes it will be obsolete once Proxmox backports the fixes, which has since happened.

---

*16 gists · 215,996 bytes · 28 comments between them.*

> Generated after the gist consolidation. If you migrate one, remember to add a
> "moved" banner to the gist the way the other 47 have, and drop it from this list.
