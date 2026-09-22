---
title: "Apps"
---

# apps

what runs as a TrueNAS catalog app here, where its storage lives, and how the
app system is put together. the one app that is **not** run this way is
[frigate](../apps/frigate.md), and that page says why.

apps are docker compose projects. the UI is a form, a template turns the
answers into a compose file, and everything is on disk and readable.

## the apps pool

apps need a pool chosen before any of them will install. mine is `fast`, the
NVMe pool, because it ends up holding container images, app databases and the
docker root:

```
/mnt/.ix-apps/            # the apps dataset
/mnt/.ix-apps/docker/     # docker root -- NOT /var/lib/docker
/mnt/.ix-apps/app_configs/<app>/
/mnt/.ix-apps/app_mounts/<app>/   # ixVolumes
```

**the apps dataset is hidden.** `.ix-apps` is created and managed by TrueNAS,
does not show up in the dataset tree in the UI, and unsetting the apps pool
takes it with everything in it.

## storage: ixVolume or your own dataset

each storage item in an app is either:

| | where it lives | pool | deleted with the app |
| --- | --- | --- | --- |
| **ixVolume** | `.ix-apps/app_mounts/<app>/` | always the apps pool | yes |
| **host path** | a dataset you made | any pool you like | no |

**ixVolumes are the right default.** they are chowned to 568 for you, they need
no dataset admin, and dying with the app is a feature for config that means
nothing without it.

they are also better protected than they look. TrueNAS snapshots them
automatically **before every app upgrade** and before a system update:

```
# .ix-apps is the MOUNTPOINT; the dataset is <pool>/ix-apps
zfs list -t snapshot -r fast/ix-apps/app_mounts/<app>
```

```text
...app_mounts/grafana/plugins@1.4.12
...app_mounts/grafana/plugins@1.4.17
...app_mounts/grafana/plugins@ix-apps-backup-system-update--2026-09-13_20:06:33
```

so a bad upgrade is recoverable, which covers the most likely way an app breaks.

### when to use your own dataset instead

two reasons, and neither is "ixVolumes are bad":

1. **you want point-in-time recovery.** a periodic snapshot task **cannot
   target an ixVolume** — middleware does not expose those datasets, and the
   task is refused with `Dataset not found`. the newest snapshot you will ever
   have is from the last time you upgraded that app. fine for a metrics
   database or a model cache; think harder about dashboards you built or chat
   history
2. **the data belongs on a different pool.** an ixVolume always lands on the
   apps pool. bulk data that wants the big pool, or that you want on spinning
   disks rather than NVMe, needs a dataset you made

[frigate](../apps/frigate.md) is the second case: its recordings are on datasets i
made, on the pool that suits them, with retention frigate manages itself.

a host path is **not** chowned for you, only ixVolumes get the automatic
permissions step. so a dataset you made as root gives permission denied on the
app's first write.

**check what the app actually runs as first.** 568 is the common case, not the
rule: open-webui runs as `0:0`, and chowning its data to 568 made it crash-loop
with sqlite `attempt to write a readonly database`, while the dataset was
writable, the mount was `rw` and the container was root. TrueNAS apps run with
`CapDrop: ALL`, so root has no `DAC_OVERRIDE` and obeys file permissions like
anyone else.

```
docker inspect ix-open-webui-open-webui-1 --format '{{.Config.User}}'
chown -R 0:0 /mnt/fast/configs/open-webui        # that app wants root
chown -R 568:568 /mnt/fast/configs/grafana       # this one wants apps
```

name them `fast/configs/<app>` so one recursive snapshot task covers every app
that needs one, see [storage](storage.md).

check what an app is actually using:

```
python3 - <<'INSPECT'
import yaml, json
path = "/mnt/.ix-apps/app_configs/APP/versions/VERSION/user_config.yaml"
print(json.dumps(yaml.safe_load(open(path))["storage"], indent=2))
INSPECT
```

## what runs here

| app | image | what for |
| --- | --- | --- |
| `prometheus` | `prom/prometheus` | metrics, scraping the exporters sysext |
| `grafana` | `grafana/grafana` | dashboards on top of prometheus |
| `glances` | `nicolargo/glances` | host overview; reads `/proc`, `/sys` and the docker socket |
| `ollama` | `ollama/ollama` | local LLM inference on a MIG slice |
| `open-webui` | `ghcr.io/open-webui/open-webui` (cuda) + valkey | front end for ollama |
| `searxng` | `searxng/searxng` | metasearch |
| `versitygw` | `ghcr.io/versity/versitygw` | S3, see [S3 with Versity Gateway](s3-versity-gateway.md) |
| `portainer-agent` | `portainer/agent` | below |

apps get a port in the 30000s by default, and are reached over the NAS's
hostname with the certificate picked in the app.

## the portainer agent

this one is a **custom app**, not a catalog one, so that the NAS appears in
[portainer](../docker/portainer.md) next to the swarm and can run stacks
from git.

Apps → Discover Apps → the three dots by **Custom App** → **Install via YAML**:

```yaml
services:
  agent:
    image: portainer/agent:2.33.7
    container_name: portainer-agent
    restart: unless-stopped
    ports:
      - "9001:9001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /mnt/.ix-apps/docker/volumes:/var/lib/docker/volumes
```

- **pin it to the portainer server's version**, from Settings or
  `curl -sk https://<portainer>:9443/api/system/status`
- the second volume is the one people get wrong: the agent expects the host's
  volumes at `/var/lib/docker/volumes` *inside* the container, and on TrueNAS
  the host side of that is `/mnt/.ix-apps/docker/volumes`
- **it is deliberately an app and not a portainer stack.** portainer must not
  be responsible for restarting the agent it reaches the host through. as an
  app, middleware owns its lifecycle and it returns after a reboot
- no `AGENT_SECRET`, matching the swarm agent. anything that can reach 9001 can
  drive docker on this box, so it belongs on a trusted LAN only

check it answers before touching portainer — a running container is not the
same as a working agent:

```
curl -sk -o /dev/null -w '%{http_code}\n' https://<nas>:9001/ping   # 204
```

then add it in Portainer as **Docker Standalone → Agent**, address
`<nas ip>:9001`.

### what portainer then shows

everything on the box, not just what it deployed: catalog apps appear as stacks
named `ix-<app>`, and anything started by hand appears too. they are still
managed by TrueNAS — editing them from portainer fights middleware.

stopped projects also appear. a stack in that list is not proof of a running
container.

## old app images are never removed

**TrueNAS pulls a new image on every app update and never deletes the old one.**
There is no cleanup anywhere in it: no API method, no timer, no cron. Mine
reached **225 GB** of stale images before I looked, eleven superseded
open-webui builds at ~11 GB each among them.

They are tagged, not dangling, so a plain `docker image prune` does not touch
them. Check with `docker system df`, then a weekly cron job as root keeps it
flat:

```
/usr/bin/docker image prune -a -f --filter until=168h
```

`until=168h` keeps the last week, so the version you ran before the most recent
update is still there to roll back to. `-a` is required, or the tagged old
versions survive.

## how an app is actually built

three files per app, under
`/mnt/.ix-apps/app_configs/<app>/versions/<version>/`:

| file | what it is |
| --- | --- |
| `questions.yaml` | the form. every option the UI can offer |
| `templates/docker-compose.yaml` | jinja, turning answers into compose |
| `user_config.yaml` | your answers |
| `templates/rendered/docker-compose.yaml` | **what actually deploys** |

the rendered file is the truth — final image tag, every bind and device, caps,
healthcheck, limits. it is JSON despite the name:

```
python3 -m json.tool < /mnt/.ix-apps/app_configs/<app>/versions/<version>/templates/rendered/docker-compose.yaml
```

it contains environment variables in plain text, so an app that takes an API key
as a variable has it in that file.

## an option the form does not offer cannot be set

`questions.yaml` is the complete list of what the UI can produce. if an option
is not there, no amount of the underlying image supporting it will help.

editing the two files locally does work, and **an app update overwrites them**.
quietly: the container still starts and still reports healthy, just without
whatever you added.

that is the whole reason [frigate](../apps/frigate.md) is not an app here.
