---
title: "Dozzle"
---

# dozzle logs

one [dozzle](https://dozzle.dev/) UI for the logs of every container on every docker host, with an agent on each host feeding it.

| piece | where | port |
| --- | --- | --- |
| hub, the UI | swarm, one replica | `8888`, host mode, on the node it runs on |
| agent | swarm, `mode: global`, one per node | `7007`, host mode |
| agent | truenas1, syn02, pi-zwave01, each its own stack | `7007` |

the hub lists every agent by the host's own address, with a name and a sidebar group:

```yaml
      - DOZZLE_REMOTE_AGENT=192.168.1.41:7007|Docker01|Swarm,192.168.1.42:7007|Docker02|Swarm,192.168.1.43:7007|docker03|Swarm,192.168.1.86:7007|truenas1|TrueNAS,192.168.1.31:7007|syn02|Other,192.168.1.96:7007|pi-zwave01|Other
```

never the keepalived VIP: it moves, and the hub would show one node's logs under another's name.

## make your own certificate pair

the hub and the agents authenticate each other with a certificate pair. the one built into the image is the same in every copy of it, so it encrypts but proves nothing: anyone who can reach port `7007` with a stock image can read every log on that host. generate your own:

```
docker run --name dozzle-certgen amir20/dozzle:v11.1.0 \
  generate-certs --cert-out /dozzle_cert.pem --key-out /dozzle_key.pem
docker cp dozzle-certgen:/dozzle_cert.pem .
docker cp dozzle-certgen:/dozzle_key.pem .
docker rm dozzle-certgen
```

- on the swarm the pair is two docker secrets, and the hub and agents read them through `DOZZLE_CERT` and `DOZZLE_KEY`
- a standalone host can't mount a swarm secret, so it gets the two files bound read-only from a host directory: `/docker-data/dozzle` on the pi, `/volume1/docker/dozzle` on syn02
- the pair is good for five years. both ends are replaced together

## deploy agents before the hub

a hub with no agents answering is an empty UI. create each host's agent stack first, then the swarm's stack, which brings up its agents and the hub together. a missing agent shows as unavailable in the hub, and is almost always a certificate mismatch.

## adding a host

1. copy the pair to the new host
2. add its agent stack, as for syn02 or the pi
3. add the host to the hub's `DOZZLE_REMOTE_AGENT` list, which redeploys the hub

[gatus](gatus.md) checks each agent's port on each host's own address.
