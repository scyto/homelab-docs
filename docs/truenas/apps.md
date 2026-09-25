---
title: "Apps"
---

# apps

what runs as a TrueNAS catalog app here, where its storage lives, and how the
app system is put together. [the arr stack](../apps/arrstack.md),
[frigate](../apps/frigate.md), [glances](../monitoring/glances.md) and the
[dozzle agent](../monitoring/dozzle.md) are portainer stacks from git instead,
see [truenas1](../docker/standalone/truenas1.md).

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

`.ix-apps` is created and managed by TrueNAS, and does not show up in the
dataset tree in the UI. **unsetting the apps pool takes it with everything in
it.**

## storage: ixVolume or your own dataset

each storage item in an app is either:

| | where it lives | pool | deleted with the app |
| --- | --- | --- | --- |
| **ixVolume** | `.ix-apps/app_mounts/<app>/` | always the apps pool | yes |
| **host path** | a dataset you made | any pool you like | no |

ixVolumes are the right default. they are chowned to 568 for you, they need no
dataset admin, and config that means nothing without its app is deleted with
it.

TrueNAS snapshots them automatically before every app upgrade and before a
system update:

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

there are two reasons:

1. you want point-in-time recovery. a periodic snapshot task cannot target an
   ixVolume: middleware does not expose those datasets, and the task is refused
   with `Dataset not found`. the newest snapshot you will have is from the last
   time you upgraded that app. that is fine for a metrics database or a model
   cache. think harder about dashboards you built or chat history
2. the data belongs on a different pool. an ixVolume always lands on the apps
   pool. bulk data that wants the big pool, or that you want on spinning disks
   rather than NVMe, needs a dataset you made

[versity](s3-versity-gateway.md) is the second case: its buckets are on
`rust/S3`, a dataset i made on the spinning-disk pool.

a host path is not chowned for you: only ixVolumes get the automatic
permissions step. a dataset you made as root gives permission denied on the
app's first write.

check what the app runs as first. 568 is the common case, not the rule.
open-webui runs as `0:0`, and chowning its data to 568 made it crash-loop with
sqlite `attempt to write a readonly database`, even though the dataset was
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

to see the storage an app is using:

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
| `ollama` | `ollama/ollama` | local LLM inference on a MIG slice |
| `open-webui` | `ghcr.io/open-webui/open-webui` (cuda) + valkey | front end for ollama |
| `searxng` | `searxng/searxng` | metasearch |
| `versitygw` | `ghcr.io/versity/versitygw` | S3, see [S3 with Versity Gateway](s3-versity-gateway.md) |
| `portainer-agent` | `portainer/agent` | below |

apps get a port in the 30000s by default, and are reached over the NAS's
hostname with the certificate picked in the app.

## time zone

catalog apps take their time zone from the app's own `TZ` value. versitygw and
open-webui show it in the form, as Timezone. grafana, prometheus, searxng and
ollama have no such field, so theirs is set through the API:

```
midclt call -j app.update <app> '{"values": {"TZ": "America/Los_Angeles"}}'
```

- never add `TZ` under Additional Environment Variables. the app library sets
  `TZ` from that value itself, and a second one fails the render with
  `already defined from the application developer`
- `app.update` merges the values you send into the app's settings, so this
  changes `TZ` and nothing else

## the portainer agent

the agent puts the NAS in [portainer](../docker/portainer.md) next to the
swarm, so the NAS can run stacks from git. it is a custom app, not a catalog
one.

Apps → Discover Apps → the three dots by Custom App → Install via YAML:

```yaml
services:
  agent:
    image: portainer/agent:2.45.1
    container_name: portainer-agent
    restart: unless-stopped
    ports:
      - "9001:9001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /mnt/.ix-apps/docker/volumes:/var/lib/docker/volumes
```

- pin it to the portainer server's version, from Settings or
  `curl -sk https://<portainer>:9443/api/system/status`, and bump the two
  together. mine is on `latest` right now, which reports 2.45.1 only because
  that is the newest release
- the agent expects the host's volumes at `/var/lib/docker/volumes` inside the
  container. on TrueNAS the host side of that is
  `/mnt/.ix-apps/docker/volumes`, which is what the second volume maps
- it is an app, not a portainer stack, because portainer must not be
  responsible for restarting the agent it reaches the host through. as an app,
  middleware owns its lifecycle and it returns after a reboot
- it has no `AGENT_SECRET`, matching the swarm agent. anything that can reach
  9001 can drive docker on this box, so it belongs on a trusted LAN only

before touching portainer, check that the agent answers:

```
curl -sk -o /dev/null -w '%{http_code}\n' https://<nas>:9001/ping   # 204
```

then add it in Portainer as Docker Standalone → Agent, with the address
`<nas ip>:9001`.

### what portainer then shows

portainer shows everything on the box, including what it did not deploy.
catalog apps appear as stacks named `ix-<app>`, and anything started by hand
appears too. TrueNAS still manages them, and editing them from portainer fights
middleware.

stopped projects appear too, so a stack in that list may have no running
container.

## the docker socket proxy

`dockerproxy` is a second custom app. it runs
`ghcr.io/tecnativa/docker-socket-proxy` with the docker socket mounted read
only. it answers `CONTAINERS`, `EVENTS`, `INFO`, `PING` and `VERSION`, and
`POST=0` refuses anything that changes state. the
[homepage](../monitoring/homepage.md) dashboard discovers the containers on
this box through it.

## old app images are never removed

TrueNAS pulls a new image on every app update and never deletes the old one.
TrueNAS has nothing that removes them: no API method, no timer, no cron. mine reached 225 GB
of stale images, including eleven superseded open-webui builds at ~11 GB each.

they are tagged, not dangling, so a plain `docker image prune` does not touch
them. check with `docker system df`. a weekly cron job as root keeps it flat:

```
/usr/bin/docker image prune -a -f --filter until=168h
```

`until=168h` keeps the last week, so the version you ran before the most recent
update is still there to roll back to. `-a` is required, or the tagged old
versions survive.

## how an app is built

each app has four files under
`/mnt/.ix-apps/app_configs/<app>/versions/<version>/`:

| file | what it is |
| --- | --- |
| `questions.yaml` | the form. every option the UI can offer |
| `templates/docker-compose.yaml` | jinja, turning answers into compose |
| `user_config.yaml` | your answers |
| `templates/rendered/docker-compose.yaml` | what deploys |

the rendered file has the final image tag, every bind and device, caps,
healthcheck and limits. it is JSON despite the name:

```
python3 -m json.tool < /mnt/.ix-apps/app_configs/<app>/versions/<version>/templates/rendered/docker-compose.yaml
```

it contains environment variables in plain text, so an app that takes an API key
as a variable has it in that file.

## options the form does not offer

`questions.yaml` is the complete list of what the UI can produce. an option
that is not there cannot be set, even if the underlying image supports it.

editing `questions.yaml` and the compose template locally does work, but **an
app update overwrites them**. the container still starts and still reports healthy, without whatever
you added.

that is why [frigate](../apps/frigate.md) is not an app here.

## app gotchas

these took me a while. each starts with the symptom.

### an app starts and immediately stops, and the UI shows no logs

the UI has nothing to show for a container that exits straight away. docker
still has the logs. apps are compose projects named `ix-<app name>`:

```
docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -i <app>
docker logs --tail 50 ix-<app>-<service>-1
```

`/var/log/app_lifecycle.log` only gets written when compose itself fails. if
compose started the container and the process inside exited, there is nothing
in it, and a missing file is normal.

### permission denied inside the app, on a host path

most catalog apps run as the `apps` user, uid/gid 568. give an app a Host Path
and it does not fix the ownership for you: the automatic permissions step only
runs for ixVolumes. a dataset created as root gives `permission denied` the
first time the app writes, which can look like an app that keeps stopping, or a
generic internal error.

```
ls -ldn /mnt/<pool>/<dataset>     # 0 0 means root owns it
chown 568:568 /mnt/<pool>/<dataset>
```

### host paths or ixVolumes

an ixVolume is the sensible default. it is chowned for you, config that means
nothing without its app is deleted with it, and TrueNAS snapshots it before
every app upgrade.

i use a dataset i made in two cases. a periodic snapshot task cannot target an
ixVolume at all, so point-in-time recovery needs a dataset. and an ixVolume
always lands on the apps pool, so data that belongs on a different pool needs
one too. see
[storage: ixVolume or your own dataset](#storage-ixvolume-or-your-own-dataset).

anything left under `.ix-apps` is also caught by the automatic snapshots
TrueNAS takes before an update, and that causes its own problem, see
[storage and snapshots](storage.md).

### certificates

pick the TrueNAS certificate in the app and use the full hostname it was issued
for. the short hostname fails TLS verification, and clients like portainer will
refuse it.

when the certificate changes, TrueNAS redeploys the apps using it. an acme
renewal restarts the app, and there is nothing to do by hand.

only apps get this. a stack you run yourself binds the certificate files and
keeps serving the old certificate until you restart it, see
[frigate](../apps/frigate.md#certificates).
