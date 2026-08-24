---
title: "unifi poller swarm template"
source_gist: https://gist.github.com/scyto/87c2f8fcca1c6c693bab7d68f1e6835e
---

# unifi poller swarm template

!!! note

    the project is called **UnPoller** now,
    [unpoller/unpoller](https://github.com/unpoller/unpoller). the old
    `unifi-poller` name still redirects. i still run this and i maintain the
    image for the project.

## Description
This is my most complex stack to date.  It runs the unifi-poller (uPoller) application consisting of an influx database, grafana dashboard and the uPoller collector.

## State Considerations for SWARM
This has a lot of state (database, provisioning directory for granfa, state for grafana, config file for upoller, etc.)

This time i chose to store each of these in their own glusterfs volume mount using the gluster volumefs driver.

This has the advatages of creating folders that alread have the uid:gid of the grafan container (instead of messing around with chown and chmod)

The use of clustered volume allows swarm to start containers on any node as needed.

Once the containers have started for the first time you can provision grafan by copyying the content of the provisoning folder [here](https://github.com/scyto/uploller-grafana-provsioning) into /gluster-vol1/gf_provoisioning and the upoller datasource and dashboards will auto provision.  Make sure to edit `influxdb.yml` to update database password and username set in the stack. If it doesn't provision within a few minutes restart the container.  


## Network Considerations
Only the granfan container needs to be published externally.  It can be reached by any warm node IP or the keepalived IP.
There is no need to conigure any form of name resolution for inter container communication.  

Each container shares the same network and so each container can be used using the service name as this is provdided by docker. As such each containers can reach other by using servicename (as see in the `- UP_INFLUXDB_URL=http://influxdb:8086` env var as an example,
(people over think DNS in containers! just remeber you can ping any service name from any container that shares a network!)

## Placement Considerations
None, by default this template will result in a single replica of each container.
It doesn't matter if containers start on different nodes.

```
version: "3"
services:
  influxdb:
    restart: always
    image: influxdb:1.8
    volumes:
      - influxdb:/var/lib/influxdb
    environment:
      - INFLUXDB_DB=unifi
      - INFLUXDB_ADMIN_USER=unifi
      - INFLUXDB_ADMIN_PASSWORD=unifi

  grafana:
    image: grafana/grafana
    restart: always
    depends_on:
      - influxdb
    ports:
      - '3000:3000'
    volumes:
      - grafana:/var/lib/grafana  
      - gf_provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_INSTALL_PLUGINS=grafana-clock-panel,natel-discrete-panel,grafana-piechart-panel
      - UP_INFLUXDB_URL=http://influxdb:8086

  un-poller:
    image: golift/unifi-poller:latest
    restart: always
    depends_on:
      - influxdb
    environment:
      - UP_UNIFI_DEFAULT_URL=https://192.168.1.1  #IP of your UDM pro (if you have a USG please uPoller project docs)
      - UP_UNIFI_DEFAULT_USER=<user you set in unifi>
      - UP_UNIFI_DEFAULT_PASS=<password you set in unif>
      - UP_UNIFI_DEFAULT_SAVE_SITES=true
      - UP_UNIFI_DEFAULT_SITE_0=default
      - UP_INFLUXDB_URL=http://influxdb:8086
    volumes:
      - poller:/config

volumes:
  influxdb:
    driver: gluster-vol1
  grafana:
    driver: gluster-vol1
  poller:
    driver: gluster-vol1
  gf_provisioning:
    driver: gluster-vol1
```
