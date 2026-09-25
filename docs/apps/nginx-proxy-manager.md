---
title: "Nginx Proxy Manager swarm template"
source_gist: https://gist.github.com/scyto/f18336f9eaa0c7205790066a25fd5868
---

# Nginx Proxy Manager swarm template

## Description
This template runs my experimental NPM service as part of evaluating if i should stop using my hand crafted nginx reverse proxy.
Note change your passwords and don't use the examples bellow :-) )

Update as of 2026.09.24: this is how i first set it up. what i run now is [at the end](#what-i-run-now).

## State Considerations for SWARM
This container has a database, as such I store the data on the gluster volume.
I am currenlty using a mount point to store the voume data on glusterfs.
I restrict to 1 instance of each container to avoid database corruption from having two instances.
Change example usernames and passwords as needed.
leave hostname as db (name resolution works fine using the method)
if you place the database in different stack / want to use an existing datbase then both stacks need to share a network

## Network Considerations
none, this published default ports of 80, 443 and 81 (admin) for this container, it can be reached by swarmIP:81

## Placement Considerations
This uses glusterfs to allow replica to run on any node.
I hard set 1 replica (even though thats default) to avoid corruption of database.  Not sure it will corrupt, this is just my own caution).


```
version: "3"
services:
  app:
    image: 'jc21/nginx-proxy-manager:latest'
    restart: always
    ports:
      # These ports are in format <host-port>:<container-port>
      - '80:80' # Public HTTP Port
      - '443:443' # Public HTTPS Port
      - '81:81' # Admin Web Port
      # Add any other Stream port you want to expose
      # - '21:21' # FTP
    environment:
      DB_MYSQL_HOST: "db"
      DB_MYSQL_PORT: 3306
      DB_MYSQL_USER: "npm"
      DB_MYSQL_PASSWORD: "npm"
      DB_MYSQL_NAME: "npm"
      # Uncomment this if IPv6 is not enabled on your host
      DISABLE_IPV6: 'true'
    volumes:
      - /mnt/gluster-vol1/nginx/data:/data
      - /mnt/gluster-vol1/nginx/letsencrypt:/etc/letsencrypt
    depends_on:
      - db
    deploy:
      mode: replicated
      replicas: 1    

  db:
    image: 'jc21/mariadb-aria:latest'
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: 'npm'
      MYSQL_DATABASE: 'npm'
      MYSQL_USER: 'npm'
      MYSQL_PASSWORD: 'npm'
    volumes:
      - /mnt/gluster-vol1/nginx/mysql:/var/lib/mysql
    deploy:
      mode: replicated
      replicas: 1
```

## what i run now

- npm is my reverse proxy now
- it publishes 80, 443 and 81 as 180, 1443 and 181
- the data and the database are named binds on cephfs, see [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts)
- both services read their passwords from swarm secrets through entrypoint wrappers, see [secrets](../secrets/index.md#option-3-an-entrypoint-wrapper)

--8<-- "blocks/swarm/npm/compose.yml.md"
