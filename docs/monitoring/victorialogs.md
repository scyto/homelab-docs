---
title: "VictoriaLogs"
---

# victorialogs

[VictoriaLogs](https://docs.victoriametrics.com/victorialogs/) is the log
store. today it holds the UniFi controller's events, sent by syslog: a device
going offline, why a client was disconnected, STP changes, threats blocked.
the three [UPS cards](../ups/index.md#what-watches-the-cards)
send their logs too. it runs on truenas1. checked against VictoriaLogs 1.53.0 and UniFi Network
10.6.

i added it the day after [unpoller](unpoller.md). UnPoller records what
changed on the network and when; it can't record why. the controller exports
the why over syslog, and until this nothing was listening.

--8<-- "blocks/truenas1/victorialogs/compose.yml.md"

## why this one

- it takes syslog directly, so the controller points at it and that is the
  whole pipeline. loki would need a collector in between
- it parses the CEF format UniFi sends into fields: `cef.name`,
  `cef.severity`, and one `cef.extension.UNIFI*` field per attribute, so a
  query is a field filter, not text parsing
- it is one small binary with one data directory
- it accepts loki's push format, so UnPoller's alarms can go to it later
  without adding loki

## before you deploy

1. a dataset of its own for the data, `fast/victorialogs`, mounted at
   `/mnt/fast/victorialogs`. not under `fast/configs`: that tree is snapshotted
   hourly and replicated, and a log store rewrites its files all day, so every
   snapshot would pin a copy
2. the password for the HTTP side. generate one, record it in the
   [secret store](../secrets/add.md) as `victorialogs_http_password`, and write
   it to the file the stack binds, `/mnt/fast/configs/victorialogs/http_password`:
   root, mode `600`, no trailing newline, so its size is the password's length.
   the container runs as root, so a root-only file is readable

both binds have `create_host_path: false`, so a missing dataset or file fails
the deploy. docker would otherwise create an empty directory in its place, and
VictoriaLogs would start, store logs inside the container's own layer, and
lose them at the next redeploy.

## who can do what

| port | what | login |
| --- | --- | --- |
| `514` udp and tcp | syslog in | none. syslog has none and the gateway offers none, so what is in here is whatever the lan chose to say |
| `9428` | queries, the UI at `/select/vmui`, `/metrics` | basic auth, user `logs`, the password above |
| `9428/health` | is it up | none, so [gatus](gatus.md) needs no credential |

deleting is off: the `/delete` endpoints need `-delete.enable`, which is not
set, so nothing with the password can remove an entry either.

logs carry more than they look like they do: client names and MAC addresses
today, and whatever a host writes to its journal later. that is why the login
is there from day one.

## placement considerations

truenas1, not the swarm, for the same reason as UnPoller: it is on a different
UPS from the proxmox cluster, so the store records a cluster outage instead of
being part of it.

## pointing unifi at it

on the controller: settings, system, advanced, activity logging, **SIEM
server**, address `192.168.1.86`, port `514`. i send every content type plus
debug logs. **netconsole** can point at the same address and port; that is the
devices' raw kernel output, not syslog, and it is stored as plain messages with
no `cef` fields.

## pointing the ups cards at it

on each RMCARD205, **Log** > **Syslog**: facility code **Local 0**, then **Add
Server** `192.168.1.86`, port `514`, UDP. **Send test** should land as `This
is test message from <the card's address>`.

- the card's own events, link, reboot, power, are then on record
- the card uses its own system name as the syslog hostname: `Bottom` for the
  basement card, `Shelf` for the study card and `Small` for the smc closet
  card, with `app_name` `UPS(192.168.1.72)`, `UPS(192.168.1.73)` and
  `UPS(192.168.1.71)`
- nothing else on the lan sends as `local0`, so `facility_keyword:local0` is
  the cards alone

## check it works

- the container's log starts with the flags, with `-httpAuth.password="secret"`:
  the file was read and the value was not printed
- `/mnt/fast/victorialogs/partitions/<today>` exists and grows. mine went from
  230 KB to 526 KB in the first thirty seconds
- this returns the newest events with their CEF names. it asks for the password:

    ```bash
    curl -s -u logs 'http://192.168.1.86:9428/select/logsql/query?query=cef.name:*&limit=3'
    ```

- in one of them, `_time` equals the `UNIFIutcTime` inside the message. the
  gateway sends local time with no zone, and `-syslog.timezone` is what turns
  it into the right instant. if the two differ by hours, that flag is wrong

[gatus](gatus.md) checks `/health`:

```yaml title="swarm/gatus/config/40-truenas.yaml"
  - name: victorialogs
    group: truenas
    url: "http://192.168.1.86:9428/health"
    interval: 120s
    ui:
      resolve-successful-conditions: true
    conditions: ["[STATUS] == 200"]
```

that says the process is up and serving, not that events are arriving. whether
UniFi or the UPS cards are still sending is a query that needs the password.

## one thing to know when querying

`_msg` is empty on UniFi's events. the text is in `cef.extension.msg`, and the
syslog receiver has no flag to copy it there, so add a pipe:

```text
cef.name:* | copy cef.extension.msg as _msg
```

the UI shows `_msg` first, so without this every row reads
`missing _msg field`.

## queries i use

| question | query |
| --- | --- |
| everything from UniFi in the last hour, readable | `_time:1h cef.name:* \| copy cef.extension.msg as _msg` |
| how many of each event today | `_time:1d cef.name:* \| stats by (cef.name) count() events` |
| every client drop from one access point | `cef.name:="WiFi Client Disconnected" cef.extension.UNIFIlastConnectedToDeviceName:="Master Bedroom"` |
| one client's history, by MAC | `cef.extension.UNIFIclientMac:="d0:d2:b0:8d:b2:4d" \| fields _time, cef.name, cef.extension.msg` |
| anything the gateway rated severe | `cef.severity:>=7 \| copy cef.extension.msg as _msg` |
| a window around an outage | `_time:[2026-10-01T21:35:00-07:00, 2026-10-01T21:55:00-07:00] cef.name:* \| copy cef.extension.msg as _msg` |
| everything the UPS cards said | `facility_keyword:local0` |

## retention

30 days, with a ceiling of 50 GiB so a noisy source fills its own allowance
and not the pool. whichever is reached first drops the oldest day.

## memory

VictoriaLogs lets its caches grow to 60% of the host's memory by default. it
uses what the data needs, and UniFi alone is small, so there is no limit on the
stack yet. i will add `mem_limit` before the hosts' journals go in.
