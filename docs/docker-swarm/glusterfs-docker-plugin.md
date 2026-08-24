---
title: "installing a glusterfs volume plugin"
source_gist: https://gist.github.com/scyto/7e9d471c70f92c8b983f38cdc838998d
---

# installing a glusterfs volume plugin

## Description
I wanted a simpler way to assign gluster volumes in new stacks without having to create directories by hand
There are variety of community plugins for this.

I chose to use this one https://github.com/chrisbecke/glusterfs-volume
It creates a directory called `<stackname>_<volumename>` for each volume defined in the stack.

## Pre-reqs
Assume you setup glusterfs [per this gist here](glusterfs-install.md)

In my enviroment this is the command I used to install the plugin.

  ```
  sudo docker plugin install --alias gluster-vol1 chrisbecke/glusterfs-volume GFS_VOLUME=gluster-vol1 GFS_SERVERS=docker01.mydomain.com,docker02.mydomain.com,docker03.mydomain.com
  ```
  
  followed by
  
  ```
  sudo docker plugin enable gluster-vol1
  ```

## Example
Now when a volume needed it can be specified as follows and created on the fly.  
This example is from adguard.
  1. there are two directories needed, one for work and one for conf.
  2. these are defined at runtime by the \volumes lines after the services section
  3. in the service section these volume are called and mapped in the normal way
  
```  
version: '3.2'
services:
  adguard1:
    image: 'adguard/adguardhome:latest'
    restart: always
    volumes:
      - work:/opt/adguardhome/work
      - config:/opt/adguardhome/conf
    networks:
      - adguard1

volumes:
  work:
    driver: gluster-vol1
  config:
    driver: gluster-vol1

networks:
   adguard1:
     external: true
  ```
  
  ## Note 
  The plugin driver can't be used for a file only a directory, if you need a file you can either use docker configs or you can create the file manually in you glusterfs directory and map in as normal
  
  In the example above it would create in my configuration `\mount\glustervol\adguard_config` and `\mount\glustervol\adguard_work` and these would be mapped into the container
