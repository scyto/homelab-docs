---
title: "Changelog"
---

# changelog

every publish of this site, newest first. times are pacific.

the pages are staged in a private repo that also holds my stacks, tools and CI.
most publishes document homelab changes made since the one before, and **kind**
says which:

- **docs**: the pages only
- **docs + features**: something new in the homelab
- **docs + fixes**: something in the homelab that was broken and now works
- **docs + features + fixes**: both

## pace

<!-- pace:start -->

- **24 publishes in 34 days**, from 2026-08-23 18:43 to 2026-09-25 23:06. the busiest day was 2026-09-15, with six publishes
- **220 pull requests merged** in the private repo over the same time: 80 to the docs, 140 to stacks, tools and CI. the busiest day was 2026-09-24, with 50

| week starting | publishes | docs changes | stack, tool and CI changes |
| --- | --- | --- | --- |
| 2026-09-21 | 8 | 47 | 55 |
| 2026-09-14 | 11 | 27 | 51 |
| 2026-09-07 | 0 | 0 | 0 |
| 2026-08-31 | 0 | 0 | 0 |
| 2026-08-24 | 2 | 4 | 24 |
| 2026-08-17 | 3 | 2 | 10 |

<!-- pace:end -->

## publishes

| when | publish | kind | what changed |
| --- | --- | --- | --- |
| 2026-09-25 23:06 | [#30](https://github.com/scyto/homelab-docs/pull/30) | docs + features | wordpress and nginx proxy manager keep an hourly consistent dump of their databases, and gatus copies its SQLite database through the fork, so every cephfs backup holds a copy it can restore. wordpress keeps two days of binary logs for rewinding to a minute |
| 2026-09-25 18:50 | [#29](https://github.com/scyto/homelab-docs/pull/29) | docs + fixes | the adguards recover when proxmox re-plugs a docker VM's network card: a healthcheck on each macvlan address, a placement rule each way, and the macvlan shim built by `eth0`'s own stanza. found after a card change left one adguard down for a day |
| 2026-09-25 17:28 | [#28](https://github.com/scyto/homelab-docs/pull/28) | docs + features | cephfs backups run in a container on the proxmox cluster that any node can run: hourly snapshots, the backup to PBS, and a restore check. how pbs1 is built on truenas, with one static address |
| 2026-09-25 13:07 | [#27](https://github.com/scyto/homelab-docs/pull/27) | docs + features | my review of the home page and the apps pages. five gist app pages describe what runs now. the arr stack's VPN settings explained, with its web UIs open to the lan only. zigbee2mqtt deployed on the pi |
| 2026-09-25 08:02 | [#26](https://github.com/scyto/homelab-docs/pull/26) | docs + features + fixes | every section checked against the running systems and corrected, 214 files. app and monitoring pages show the stack files that actually deploy, with notes on the lines that matter. new pages for the ESP border router, checking the thread mesh, cephfs start guards, config from git and the key-manager. previous and next links, and plain sentences throughout. in the same days: the offsite copy of PBS to azure repaired, and a CI check that stops private values reaching this site |
| 2026-09-22 23:33 | [#25](https://github.com/scyto/homelab-docs/pull/25) | docs + features | IPv6 on the docker hosts, routed with no NAT66, and the traps that look like something else. the macvlan shim that lets a node reach the adguard running on it. portainer environments addressed correctly, and a cold copy of portainer before each upgrade |
| 2026-09-22 12:36 | [#24](https://github.com/scyto/homelab-docs/pull/24) | docs | why portainer's force redeployment stays off, and a current screenshot of the deploy ruleset |
| 2026-09-22 09:55 | [#23](https://github.com/scyto/homelab-docs/pull/23) | docs + features + fixes | the site restructured into docker, apps and monitoring sections, with the standalone docker hosts, more truenas and raspberry pi pages, and wordpress multisite. the 29 pages that moved redirect. behind it, 51 changes in two days: a homepage dashboard that discovers its tiles, gatus replacing uptime kuma with its checks in git, dozzle and glances on every host, config delivered from git, and every container on pacific time |
| 2026-09-20 08:54 | [#22](https://github.com/scyto/homelab-docs/pull/22) | docs + features | a truenas section, seven pages on how the box is built, and secrets as its own top-level section. the acme.sh pages for the BMC and synology certificates. frigate and the arr stack moved into git on truenas |
| 2026-09-19 16:36 | [#21](https://github.com/scyto/homelab-docs/pull/21) | docs | two fixes to the truenas passthrough page: an nvme drive that was passed through but never bound to vfio, and a step that actually loads the vfio modules |
| 2026-09-19 16:04 | [#20](https://github.com/scyto/homelab-docs/pull/20) | docs | how truenas ran as a VM on proxmox for a year, and the host-side guards that kept proxmox off its passed-through disks |
| 2026-09-16 12:37 | [#19](https://github.com/scyto/homelab-docs/pull/19) | docs | numbered steps on the proxmox pages that restarted at 1 now count through. a checker catches the cause, which it found in 28 places |
| 2026-09-16 11:53 | [#18](https://github.com/scyto/homelab-docs/pull/18) | docs + features | omni-tools and bentopdf on the swarm, and which git reference to pick when adding a stack |
| 2026-09-15 21:34 | [#12](https://github.com/scyto/homelab-docs/pull/12) | docs | mkdocs-material 9.5.44 to 9.7.7 |
| 2026-09-15 21:25 | [#17](https://github.com/scyto/homelab-docs/pull/17) | docs | what a standalone docker host shares with the swarm |
| 2026-09-15 21:08 | [#16](https://github.com/scyto/homelab-docs/pull/16) | docs | thread: clipboard and state commands that run on each platform |
| 2026-09-15 19:15 | [#15](https://github.com/scyto/homelab-docs/pull/15) | docs | thread: which ESP-IDF tree windows uses, and the board's own name |
| 2026-09-15 18:24 | [#14](https://github.com/scyto/homelab-docs/pull/14) | docs + features | the ESP border router from an unflashed board: parts, ESP-IDF on each OS, flashing, and joining it from home assistant. an optional firmware patch names each board after its MAC. the pi's stacks deploy from git. 34 lists that rendered as paragraphs now render as lists |
| 2026-09-15 16:58 | [#13](https://github.com/scyto/homelab-docs/pull/13) | docs + features | backups, thread, raspberry pi and truenas sections, written from the running systems: the thread border routers with a firmware update and a failover test, and the pi as a GPS time source. the cephfs client mount rewritten from a tested run |
| 2026-08-26 11:05 | [a937c79](https://github.com/scyto/homelab-docs/commit/a937c79) | docs | typos and clearer wording, edited on github |
| 2026-08-24 12:03 | [#11](https://github.com/scyto/homelab-docs/pull/11) | docs + features | four swarm pages: stacks in git, secrets, image updates with renovate, and troubleshooting. the home page icons render, where they had shown as text |
| 2026-08-23 19:05 | [7e36498](https://github.com/scyto/homelab-docs/commit/7e36498) | docs | comments on the ten busiest pages, through giscus |
| 2026-08-23 18:53 | [765b1e5](https://github.com/scyto/homelab-docs/commit/765b1e5) | docs | a list of the 16 gists not yet moved to the site |
| 2026-08-23 18:43 | [100397a](https://github.com/scyto/homelab-docs/commit/100397a) | docs | the site: my proxmox and docker gists brought together in mkdocs |
