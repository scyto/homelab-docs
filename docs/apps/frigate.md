---
title: "Frigate"
---

# frigate

frigate is my NVR, with eight cameras and four inference accelerators. it runs on
the NAS because that is where the
[accelerators](../truenas/hardware-and-base-install.md#hardware) and the disk are.

it isn't a TrueNAS app. [portainer](../truenas/apps.md#the-portainer-agent)
deploys it from git as a compose stack, like truenas1's other
[stacks](../docker/standalone/truenas1.md#stacks-from-git).

--8<-- "blocks/truenas1/frigate/compose.yml.md"

## before you deploy

1. check the hardware is there:

    ```
    ls -l /dev/memx0 /dev/hailo0 /dev/apex_*
    ```

    - docker refuses to start a container whose device node is missing

2. create `/mnt/fast/configs/frigate/frigate_plus_api_key` holding only the
   Frigate+ key, owned by root with mode 600. the compose binds it read-only at
   `/run/secrets/PLUS_API_KEY`

    - docker creates a directory at a missing bind source, so the file has to
      exist before the first deploy

## why it isn't a catalog app

the MemryX MX3 detector needs the container to run privileged. the device node
alone is not enough, because the runtime talks to the `mxa-manager` daemon, see
[sysexts](../truenas/sysexts.md#memryx-in-particular).

the catalog app has a Devices list but no privileged toggle. editing the app's
`questions.yaml` and its compose template adds one, and i offered that upstream
as [truenas/apps#5164](https://github.com/truenas/apps/pull/5164). it was
declined.

an app update overwrites both files, and nothing in the UI says the setting has
gone. the container still starts, passes its healthcheck and records, but with
three detectors instead of four, because the one that needs privileged can't
initialise. so i own the compose file.

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

frigate round-robins detection across them, so the number that matters is their
combined throughput, not any one card's latency.

## the compose, and why each part is there

### devices and the daemon socket

the compose passes in all four device nodes and mounts the MX3's socket
directory:

```yaml title="compose.yml"
    devices:
      - /dev/apex_0:/dev/apex_0
      - /dev/apex_1:/dev/apex_1
      - /dev/hailo0:/dev/hailo0
      - /dev/memx0:/dev/memx0
    volumes:
      - /run/mxa_manager:/run/mxa_manager
```

it mounts the whole directory, not one socket, because the directory holds
several.

### privileged, with a capability list

the compose sets `privileged` and a capability list:

```yaml title="compose.yml"
    privileged: true
    cap_drop: [ALL]
    cap_add: [CHOWN, FOWNER, DAC_OVERRIDE, SETGID, SETUID, PERFMON, KILL]
```

under `privileged` the capability list is advisory. i keep it so that if the
MX3 ever stops needing privileged, removing that one line leaves a correct set,
not an empty one.

### one MIG slice for ffmpeg

ffmpeg decodes on one MIG slice of the GPU, not the whole GPU:

```yaml title="compose.yml"
    environment:
      NVIDIA_DRIVER_CAPABILITIES: all
      NVIDIA_VISIBLE_DEVICES: MIG-<uuid>
      CUDA_VISIBLE_DEVICES: MIG-<uuid>
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: [MIG-<uuid>]
              capabilities: [gpu]
```

the host's docker default runtime is already `nvidia`, so the compose needs no
`runtime:` line. get the UUID from `nvidia-smi -L`. it goes in both variables
and in the reservation.

## storage

| path | dataset | holds |
| --- | --- | --- |
| `/config` | `fast/configs/frigate` | `config.yaml`, the sqlite database, model cache |
| `/media` | `fast/frigate/media` | recordings, clips, exports |
| `/tmp/cache` | `fast/frigate/cache` | in-progress recording segments |

- **config is the only irreplaceable one**, and the only one snapshotted. media
  and cache must not be, see [storage](../truenas/storage.md#the-rule)
- all three are host paths on datasets i made, not ixVolumes
- cache churns hard. it is scratch, and frigate rebuilds it

## certificates

frigate serves TLS itself, so the certificate is bound in from the TrueNAS
store:

```yaml title="compose.yml"
    volumes:
      - /etc/certificates/frigate_cert.crt:/etc/letsencrypt/live/frigate/fullchain.pem:ro
      - /etc/certificates/frigate_cert.key:/etc/letsencrypt/live/frigate/privkey.pem:ro
```

leaving the app catalog made one thing worse. TrueNAS renews the certificate in
place, and as an app frigate would be restarted to pick it up. TrueNAS doesn't
manage this stack, so frigate keeps serving the old certificate until something
restarts it, which i now have to remember.

## one portainer quirk

portainer deploys standalone stacks with the compose it bundles, which can be
older than the daemon underneath. on a host running engine 29.x, mine refused
the stack with:

```
can't set healthcheck.start_interval as feature require Docker Engine v25 or later
```

so the compose file leaves that field out. without it the healthcheck runs at
its normal interval during startup, and the container reports healthy slightly
later. nothing else changes.

## checking it

the healthcheck prints why it failed:

```
docker inspect --format '{{json .State.Health.Log}}' frigate | python3 -m json.tool | tail -8
```

to count the detectors by hand:

```
docker exec frigate ps -eo args | grep -c 'frigate.detector:'     # expect 4
```

the inference times show that the cards are in use, not only present:

```
docker exec frigate curl -s http://127.0.0.1:5000/api/stats | python3 -m json.tool | head -40
```

`detectors` lists each detector with an inference speed. `cameras` lists camera
and detection fps per camera.
