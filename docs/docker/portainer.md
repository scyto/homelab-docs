---
title: "Portainer"
source_gist: https://gist.github.com/scyto/a57d63a3b905b24e9eb25618848c8e80
comments: true
---

# portainer

one portainer runs all six nodes from one UI: the swarm's three and the three [standalone hosts](standalone/index.md).

i run the business edition on the paid home & student licence. it costs US$155 a year and covers up to 15 nodes with every business feature, for personal use only. i pay for it because the free business licence covers 3 nodes and i have 6.

the business feature this setup depends on is role based access. the [homepage dashboard](../monitoring/homepage.md)'s api token belongs to a user who has read access through the helpdesk role on every environment.

on the swarm it is two stacks: the server, and an agent on every node. together they replace portainer's [stock swarm file](https://downloads.portainer.io/ee-lts/portainer-agent-stack.yml).

--8<-- "blocks/swarm/portainer/compose.yml.md"

--8<-- "blocks/swarm/agent/compose.yml.md"

apart from names, the server's file differs from the stock one in three ways: it has no agent service, the image is pinned to a version instead of `lts`, and the data volume is bound to the replicated storage. that lets the server start on any manager and find its database.

## install on the swarm

on one manager:

1. create the data folder on the cephfs mount:

    ```
    sudo mkdir -p /mnt/docker-cephFS/portainer_data
    ```

    - a missing folder fails the task, because the data volume binds its folder by path

2. delete the `command:` line (`-H tcp://tasks.agent:9001 --tlsskipverify`) from the downloaded file, then deploy the server from it:

    ```
    docker stack deploy -c portainer-compose.yml portainer
    ```

    - the line is left from the stock file. it names an agent the server can't resolve, and the server only reads it on a first start, before it has an environment. without the line the server starts with no environment, and step 5 adds one
    - the UI is on `https://<node>:9443`. `9000` serves it over plain http, and `8000` is the tunnel for edge agents, which i don't use

3. browse to it, create the admin user and enter the licence key
4. start a temporary agent on a spare port:

    ```
    docker run -d --name temp-agent -p 9002:9001 \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /var/lib/docker/volumes:/var/lib/docker/volumes \
      portainer/agent:2.45.1
    ```

    - portainer creates a stack through an environment's agent, so the agent stack needs an agent before it exists
    - `9002` leaves `9001` free for the agent stack, which publishes it on every node

5. in portainer, add a docker swarm environment using the agent, at `<manager>:9002`
6. create the `agent` stack from git, as in [cut a stack over](gitops-with-portainer.md#6-cut-a-stack-over): reference `refs/heads/deploy/swarm/agent`, compose path `stacks/swarm/agent/compose.yml`
7. point the environment at the keepalived VIP, `192.168.1.45:9001`, and check the agent runs on every node:

    ```
    docker stack services agent
    ```

    - `REPLICAS` reads `3/3`, one task on each of the three nodes

8. remove the temporary agent:

    ```
    docker rm -f temp-agent
    ```

9. add the standalone hosts, see [add a host](standalone/add-a-host.md)

## agents on every endpoint

| environment | agent | how it is installed |
| --- | --- | --- |
| swarm | a global service, on `9001` on each node | the agent stack above, from git |
| truenas1 | truenas custom app | [truenas apps](../truenas/apps.md) |
| syn02, pi-zwave01 | a container, `restart: always` | [add a host](standalone/add-a-host.md) |

each environment points at an address on 9001. the swarm's is the keepalived VIP, and each standalone host's is the host itself. portainer reaches the swarm through that address, and removing the agent stack cuts it off.

## signing in with entra

users sign in to portainer with their entra ID accounts, through portainer's
own oauth setting. in settings → authentication → oauth, choose the microsoft
provider with a custom configuration.

1. register an app in entra with a web redirect URI of portainer's own
   address, `https://portainer.mydomain.com`, and a client secret

    - set *assignment required* on its enterprise application and assign who
      may sign in

2. fill in the form:

    | field | value |
    | --- | --- |
    | client ID, client secret | the app's |
    | authorization URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize` |
    | access token URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token` |
    | resource URL | `https://graph.microsoft.com/v1.0/me` |
    | redirect URL | portainer's own address, the same as the registered redirect URI |
    | logout URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/logout` |
    | user identifier | `userPrincipalName` |
    | scopes | `openid profile` |

    - the tenant's own userinfo endpoint, `https://graph.microsoft.com/oidc/userinfo`,
      has no `userPrincipalName`, and signing in then fails with "failed to
      extract username from oauth resource"

3. turn automatic user provisioning off, and create each user in portainer,
   named with their user principal name, before you log out

    - with it off, only users made in portainer get in. without the user, your
      first sign-in with entra has nowhere to land

the initial admin can always log in with a password, whatever the setting,
and API keys skip the login altogether. so from outside,
[traefik](../apps/traefik.md) keeps entra in front of `/api/auth` and of any
request that carries an API key.

## what deploys from git

portainer itself is the one stack not deployed [from git](gitops-with-portainer.md). it would be applying changes to itself, and a bad commit leaves no UI to fix it with.

the agent deploys from git like any other stack. a change to it is an ordinary service update, which the swarm manager finishes even if portainer's connection drops while the agents restart.

a broken agent compose reaches every node a few minutes after it merges, and portainer loses its view of the swarm. to recover, point the environment at the temporary agent from [install step 4](#install-on-the-swarm) while a fixed or reverted compose deploys.

## upgrades

- upgrade the server first, then the agents, and keep them on the same version. a newer server can talk to older agents, but the reverse is not guaranteed
- take a [cold copy](../backups/portainer-s3.md#cold-copies-before-an-upgrade) of the server's data before upgrading it
- renovate proposes bumps for both only through its dependency dashboard, so neither restarts until i approve it

## checking it

on a manager:

```
docker stack services portainer
docker stack services agent
```

`REPLICAS` reads `1/1` for the server and `3/3` for the agent.
