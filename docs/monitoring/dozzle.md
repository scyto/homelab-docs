---
title: "Dozzle"
---

# dozzle logs

one [dozzle](https://dozzle.dev/) UI shows the logs of every container on every docker host, fed by an agent on each host. the hub (the UI) has no docker socket, so every host reaches it through an agent, docker01 included.

| piece | where | port |
| --- | --- | --- |
| hub, the UI | swarm, one replica pinned to docker01 | `8888`, host mode, at `192.168.1.41:8888` |
| agent | swarm, `mode: global`, one per node | `7007`, host mode |
| agent | truenas1, syn02, pi-zwave01, each its own stack | `7007` |

--8<-- "blocks/swarm/dozzle/compose.yml.md"

## before you deploy

1. make your own certificate pair. the hub and the agents authenticate each other with it:

    ```
    docker run --name dozzle-certgen amir20/dozzle:v11.1.0 \
      generate-certs --cert-out /dozzle_cert.pem --key-out /dozzle_key.pem
    docker cp dozzle-certgen:/dozzle_cert.pem .
    docker cp dozzle-certgen:/dozzle_key.pem .
    docker rm dozzle-certgen
    ```

    - the image has a pair built in, and every copy has the same one. anyone who can reach port `7007` with a stock image can read every log on that host
    - the pair is valid for five years. replace it on the hub and every agent at the same time

2. on a swarm manager, make the pair two docker secrets:

    ```
    docker secret create dozzle_agent_cert_v1 dozzle_cert.pem
    docker secret create dozzle_agent_key_v1 dozzle_key.pem
    ```

    - the hub and the swarm's agents read them through `DOZZLE_CERT` and `DOZZLE_KEY`

3. copy the pair to each standalone host, into the directory its agent binds from:

    | host | directory |
    | --- | --- |
    | truenas1 | `/mnt/fast/configs/dozzle` |
    | syn02 | `/volume1/docker/dozzle` |
    | pi-zwave01 | `/docker-data/dozzle` |

    - docker creates a directory at a missing bind source, and the agent then fails its handshake
    - a host that loses its copy gets the same pair back. a new pair has to reach the hub and every agent at once

4. deploy the agents on truenas1, syn02 and pi-zwave01 first, then the swarm's stack, which brings up its agents and the hub together

    - a hub with no agents answering is an empty UI

## the agent list

the hub lists every agent by the host's own address, with a name and a sidebar group:

```yaml title="swarm/dozzle/compose.yml"
      - DOZZLE_REMOTE_AGENT=192.168.1.41:7007|Docker01|Swarm,192.168.1.42:7007|Docker02|Swarm,192.168.1.43:7007|docker03|Swarm,192.168.1.86:7007|truenas1|TrueNAS,192.168.1.31:7007|syn02|Other,192.168.1.96:7007|pi-zwave01|Other
```

don't use the keepalived VIP. it moves, and the hub would show one node's logs under another's name.

## the agents on the standalone hosts

truenas1, syn02 and pi-zwave01 are not in the swarm, so none of them can mount a swarm secret. each runs the agent as a stack of its own. it binds the pair read-only from the directory in [before you deploy](#before-you-deploy) to `/dozzle_cert.pem` and `/dozzle_key.pem`, where dozzle looks by default.

--8<-- "blocks/truenas1/dozzle/compose.yml.md"

--8<-- "blocks/syn02/dozzle/compose.yml.md"

--8<-- "blocks/pi-zwave01/dozzle/compose.yml.md"

## adding a host

1. copy the pair to the new host
2. add its agent stack, as for syn02 or the pi
3. add the host to the hub's `DOZZLE_REMOTE_AGENT` list, which redeploys the hub

## checking it

the hub's page lists the hosts, and whether it can reach each agent:

```
curl -s http://192.168.1.41:8888/ | grep '"hosts"' | jq -r '.hosts[] | "\(.name) \(.available)"'
```

```text
Docker01 true
Docker02 true
docker03 true
pi-zwave01 true
syn02 true
truenas1 true
```

`false` is an agent the hub can't reach or that refuses its certificate. [gatus](gatus.md) checks each agent's port on each host's own address.
