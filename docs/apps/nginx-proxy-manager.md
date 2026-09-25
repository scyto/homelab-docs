---
title: "Nginx Proxy Manager swarm template"
source_gist: https://gist.github.com/scyto/f18336f9eaa0c7205790066a25fd5868
---

# Nginx Proxy Manager swarm template

## Description
This template runs NPM, my reverse proxy.

## State Considerations for SWARM
This container has a database. The data, the certificates and the database are named binds on cephfs, see [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts).
I restrict to 1 instance of each container to avoid database corruption from having two instances.
Both services read their passwords from swarm secrets through entrypoint wrappers, see [secrets](../secrets/index.md#option-3-an-entrypoint-wrapper).
Leave hostname as db (name resolution works fine using this method).
If you place the database in a different stack / want to use an existing database then both stacks need to share a network.

## Network Considerations
This publishes 80, 443 and 81 (admin) as 180, 1443 and 181, so the admin UI is at swarmIP:181.

## Placement Considerations
cephfs allows the replica to run on any node.
I hard set 1 replica (even though that's default) to avoid corruption of the database.  Not sure it will corrupt, this is just my own caution.

--8<-- "blocks/swarm/npm/compose.yml.md"
