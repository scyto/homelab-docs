---
title: "Frigate"
---

# frigate

the NVR. eight cameras, four inference accelerators, running on the NAS because
that is where the [accelerators](hardware-and-base-install.md#hardware) and the
disk are.

it is the one workload here that is **not** a TrueNAS app. it runs as a compose
stack that [portainer](apps.md#the-portainer-agent) deploys from git.

## why not a catalog app

the MemryX MX3 detector needs the container to run **privileged**. the device
node alone is not enough — the runtime talks to the `mxa-manager` daemon, see
[sysexts](sysexts.md#memryx-in-particular).

the catalog app exposes a **Devices** list but has no privileged toggle. that
option can be added by editing the app's `questions.yaml` and its compose
template, and i did; i offered it upstream as
[truenas/apps#5164](https://github.com/truenas/apps/pull/5164) and it was
declined.

**an app update overwrites both files.** what makes that worse than annoying is
how it fails: the container still starts, still passes its healthcheck and
still records — it just runs three detectors instead of four, because the one
needing privileged cannot initialise. nothing in the UI says a setting has gone.

so the choice is between re-applying an edit after every update and hoping to
notice when it is lost, or owning the compose file. i own the compose file.

## what portainer gives it

- the compose file is in git, reviewed, and deployed from a branch
- `privileged: true` is in that file and nothing else rewrites it
- the same place manages the swarm, so it is one list of stacks

## detectors

all four run at once, each with its own model:

| detector | device | accelerator |
| --- | --- | --- |
| `hailo8l` | `PCIe` | Hailo-8 |
| `coral1` | `pci:0` | Coral Edge TPU |
| `coral2` | `pci:1` | Coral Edge TPU |
| `memryx` | `PCIe:0` | MemryX MX3 |

frigate round-robins detection across them, so the useful number is aggregate
throughput rather than any one card's latency.

## the compose, and why each part is there

**devices and the daemon socket.** all four device nodes, plus the MX3's socket
directory:

```yaml
    devices:
      - /dev/apex_0:/dev/apex_0
      - /dev/apex_1:/dev/apex_1
      - /dev/hailo0:/dev/hailo0
      - /dev/memx0:/dev/memx0
    volumes:
      - /run/mxa_manager:/run/mxa_manager
```

the directory is mounted, not an individual socket — there are several.

**privileged, and the capabilities kept anyway:**

```yaml
    privileged: true
    cap_drop: [ALL]
    cap_add: [CHOWN, FOWNER, DAC_OVERRIDE, SETGID, SETUID, PERFMON, KILL]
    security_opt: [no-new-privileges=true]
    group_add: ["44", "107", "568"]     # video, render, apps
```

under `privileged` the capability list is advisory. it is kept so that if the
MX3 ever stops needing privileged, dropping one line leaves a correct set
behind rather than a blank one.

**one MIG slice, not the whole GPU**, for ffmpeg decode:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["MIG-<uuid>"]
              capabilities: [gpu]
```

the host's docker default runtime is already `nvidia`, so no `runtime:`
override is needed. get the UUID from `nvidia-smi -L`.

**host networking**, because go2rtc needs to reach the cameras directly and
frigate publishes several ports.

**512 MB of shared memory.** the image default is 64 MB, which is not enough
for this many cameras; frigate's detector processes pass frames through
`/dev/shm`.

## storage

| path | dataset | holds |
| --- | --- | --- |
| `/config` | `fast/configs/frigate` | `config.yaml`, the sqlite database, model cache |
| `/media` | `fast/frigate/media` | recordings, clips, exports |
| `/tmp/cache` | `fast/frigate/cache` | in-progress recording segments |

- **config is the only irreplaceable one**, and it is the only one snapshotted.
  media and cache must not be, see [storage](storage.md#the-rule)
- all three are host paths on datasets i made, not ixVolumes
- cache churns hard. it is scratch, and frigate rebuilds it

## certificates

frigate serves TLS itself, so the certificate is bound in from the TrueNAS
store:

```yaml
      - /etc/certificates/<cert>.crt:/etc/letsencrypt/live/<name>/fullchain.pem:ro
      - /etc/certificates/<cert>.key:/etc/letsencrypt/live/<name>/privkey.pem:ro
```

**this is the one thing that got worse by leaving the app catalog.** TrueNAS
renews the certificate in place, and as an app it would restart the app to pick
it up. a stack it does not manage keeps serving the old certificate until
something restarts it, so that is now a thing to remember.

## checking it is actually working

a healthy container proves nothing here — that is the exact failure the whole
arrangement exists to avoid. check the detectors:

```
docker exec frigate ps -eo args | grep -c 'frigate.detector:'     # expect 4
```

and the inference times, which also tell you the cards are being used rather
than merely present:

```
docker exec frigate curl -s http://127.0.0.1:5000/api/stats | python3 -m json.tool | head -40
```

`detectors` lists each with an inference speed; `cameras` lists camera and
detection fps per camera.

## one portainer quirk

portainer deploys standalone stacks with its own bundled compose, which can be
older than the daemon underneath. mine refused the stack with:

```
can't set healthcheck.start_interval as feature require Docker Engine v25 or later
```

on a host running engine 29.x. the field is dropped from the compose file;
without it the healthcheck runs at its normal interval during startup and the
container reports healthy slightly later. nothing else changes.
