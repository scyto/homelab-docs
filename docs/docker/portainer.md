---
title: "Portainer"
source_gist: https://gist.github.com/scyto/a57d63a3b905b24e9eb25618848c8e80
comments: true
---

# portainer

one portainer runs the swarm and the three [standalone hosts](standalone/index.md), six nodes in all, from one UI.

i run the business edition on the paid **home & student** licence: US$155 a year, up to 15 nodes, every business feature, personal use only. the free business licence covers 3 nodes and i have 6, which is why it's the paid one.

the business feature this setup depends on is role based access: the [homepage dashboard](../monitoring/homepage.md)'s api token belongs to a user with the helpdesk role on every environment, so it can see everything and change nothing.

## install on the swarm

on a manager node:

```
curl -L https://downloads.portainer.io/ee-lts/portainer-agent-stack.yml -o portainer-agent-stack.yml
docker stack deploy -c portainer-agent-stack.yml portainer
```

that deploys the server on a manager and the agent as a global service on every node. the UI is on `https://<node>:9443`. port `8000` is the tunnel for edge agents, i don't use them.

browse to it, create the admin user and enter the licence key.

one change from the stock file: the data volume is a bind to the replicated storage, so the server can start on any manager and find its database.

```yaml
volumes:
  data:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/portainer_data"
      o: bind
```

## agents on every endpoint

| environment | agent | how it is installed |
| --- | --- | --- |
| swarm | global service, `9001` published `mode: host` on each node | the stack above |
| truenas1 | truenas custom app | [truenas apps](../truenas/apps.md) |
| syn02, pi-zwave01 | a container, `restart: always` | [add a host](standalone/add-a-host.md) |

- keep every agent on the same version as the server. portainer's upgrade docs
  say to update the server first: it can talk to older agents, the reverse is
  not guaranteed
- **each environment points at an address on 9001**, the swarm's at the keepalived
  VIP and the standalone ones at the host. the stock file starts the server with
  `-H tcp://tasks.agent:9001`, which reads like the server finds the agents over
  the overlay, but the environment's own address is what is used. worth knowing
  before you delete an agent: that is how portainer reaches the swarm at all

## portainer is not in git, the agent is

**portainer itself** is the one stack not deployed [from git](gitops-with-portainer.md).
it would be applying changes to itself, and a bad commit leaves no UI to fix it
with. upgrades are deliberate, with a [cold copy](../backups/portainer-s3.md#cold-copies-before-an-upgrade)
taken first.

**the agent moved into git**, because portainer applying a change there is an
ordinary service update: it hands the update to the swarm manager, which
finishes it whether or not portainer's own connection blips while the agents
roll. two things to know if you do the same:

- **converting it needs a temporary agent.** portainer reaches the swarm
  *through* the agents, and converting a stack to git deletes it before
  recreating it. run a standalone agent on a manager on a spare port, point the
  environment at it for the window, convert, point back, remove it
- **a broken agent compose reaches every node a few minutes after it merges**,
  and takes portainer's view of the swarm with it. recovery is that same
  standalone agent. that is the trade for having the definition in git, where
  drift cannot hide

renovate proposes bumps for both, but only through the dependency dashboard, so
restarting the control plane is always a decision.
