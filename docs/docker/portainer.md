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

- keep every agent on the same version as the server
- the server reaches the swarm's agents through `tasks.agent` on the overlay, and the standalone ones at `<host>:9001`

## not in git

portainer and its swarm agent are the two stacks not deployed [from git](gitops-with-portainer.md): portainer can't safely redeploy itself. renovate leaves them alone too, so upgrades are by hand, with a [backup](../backups/portainer-s3.md) first.
