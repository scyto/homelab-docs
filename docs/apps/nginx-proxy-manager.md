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
A third service, `db-dump`, dumps the database to `/mnt/docker-cephFS/npm_dumps` at start and at :50 every hour, so every [cephFS backup](../backups/cephfs.md#databases) holds a consistent copy. It runs the database's image with the same script as [wordpress's hourly dump](wordpress.md#the-hourly-dump). The folder has to exist before the first deploy (`sudo mkdir -m 700 /mnt/docker-cephFS/npm_dumps`).
The tables are Aria, which has no consistent read view, so the dump uses `--lock-tables`: writers wait for it, readers carry on. The database is 0.5 MB and the dump takes under a second, and only npm's admin side uses the database, while nginx proxies from the config files npm generates.
If `mysqldump --routines` fails with `Cannot load from mysql.proc` (error 1728), the system tables were made by an older MariaDB and never upgraded. `mariadb-upgrade` inside the db container fixes that; take a dump first.
The image creates two anonymous accounts when it starts on an empty data folder, `''@'localhost'` and one for that first container's hostname, and never removes them. Nothing uses them, and `mysql -u npm` inside the db container is matched to the anonymous one instead of `npm`, so I dropped both, with the grants they leave on `test` databases. As root in the db container: `SELECT Host FROM mysql.user WHERE User = ''` gives the hostname, then `DROP USER ''@'localhost', ''@'<hostname>'; DELETE FROM mysql.db WHERE User = ''; FLUSH PRIVILEGES;`.

## Network Considerations
This publishes 80, 443 and 81 (admin) as 180, 1443 and 181, so the admin UI is at swarmIP:181.

## Placement Considerations
cephfs allows the replica to run on any node.
I hard set 1 replica (even though that's default) to avoid corruption of the database.  Not sure it will corrupt, this is just my own caution.

--8<-- "blocks/swarm/npm/compose.yml.md"

--8<-- "blocks/swarm/npm/db-dump.sh.md"
