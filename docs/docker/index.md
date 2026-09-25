---
title: "Installation Step-by-Step"
source_gist: https://gist.github.com/scyto/f4624361c4e8c3be2aad9b3f0073c7f9
comments: true
---

This (and related gists) captures how i created my docker swarm architecture.  This is intended mostly for my own notes incase i need to re-creeate anything later! As such expect some typos and possibly even an error...

# Installation Step-by-Step
Each major task has its own gist, this is to help with maitainability long term.

1. [Install Debian VM for each docker host](swarm/debian-vm-install.md)
2. [install Docker](swarm/install-docker.md)
3. [Configure Docker Swarm](swarm/configure-swarm.md)
4. [Install Portainer](portainer.md)
5. [Install KeepaliveD](swarm/keepalived.md)
6. [Using VirtioFS backed by CephFS for bind mounts (migrating from glsuterFS - WIP)](../proxmox/cephfs-virtiofs-passthrough.md)
7. [Move your stacks into git](gitops-with-portainer.md)
8. [Get secrets out of your stack definitions](../secrets/index.md)
9. [Keep images updated with Renovate](image-updates-renovate.md)
10. [Stack conventions](conventions.md)
11. [Add the standalone docker hosts](standalone/index.md)
12. [Random notes and troubleshooting](troubleshooting.md)
13. ~~[glusterFS disk prep, install & config ](deprecated/glusterfs-install.md)~~
14. ~~[gluster FS plugin for docker (optional )](deprecated/glusterfs-docker-plugin.md)~~
15. [Swarm deployed stacks](#swarm-deployed-stacks)

# Swarm Deployed Stacks

this is what runs on the swarm, as portainer listed it on 9/21/2026. every stack here deploys from git except portainer and its agent. the standalone hosts have [their own pages](standalone/index.md).

Update as of 2026.09.24: the agent deploys from git now as well. portainer itself is the one stack that doesn't.

- [adguard](../apps/adguard.md) - two dns resolvers, kept in sync
- [nginx proxy manager](../apps/nginx-proxy-manager.md) - reverse proxy and its certificates
- [oauth2-proxy](../apps/oauth2-proxy.md) - an auth proxy, running with nothing routed through it
- [cloudflare ddns](../apps/cloudflare-ddns.md) - keeps the external A record current
- acme.sh for the [ASRock Rack BMC](../apps/acme-asrock-bmc.md) and [Synology DSM](../apps/acme-synology.md) - certificates
- [mosquitto mqtt](../apps/mosquitto-mqtt.md) - mqtt broker
- [infinitude](../apps/infinitude.md) - carrier infinity thermostat control
- [wordpress](../apps/wordpress.md) - a multisite wordpress and its database
- apprise - a notifications api, with a web UI for its config
- unifi api browser - browsing the unifi controller's api
- [omni-tools](../apps/omni-tools.md) and [bentopdf](../apps/bentopdf.md) - file, text and pdf tools in the browser
- [gatus](../monitoring/gatus.md), [glances](../monitoring/glances.md), [dozzle](../monitoring/dozzle.md) and [homepage](../monitoring/homepage.md) - monitoring and the dashboard
- [auto-label nodes](../apps/auto-label-nodes.md) - labels each node with what runs on it
- docker socket proxy - read-only docker api for the dashboard
- [portainer](portainer.md) and its agent

## no longer used

- [watchtower](../apps/retired/watchtower.md)
- [shepherd](../apps/retired/shepherd.md)
- [traefik](../apps/retired/traefik.md)
- [portainer agent managed by portainer](../apps/retired/portainer-agent.md)
- [portception](../apps/retired/portception.md) - portainer deployed by portainer, do not attempt

# More Details on What and Why

## design goals:
  - ensure every container stays running if any of the following fail (one VM, one hypervisor, one docker service)
  - remove chance of blackhole requests (aka eliminate the use of DNS round robin to address the service)
  - enable the use of replicated state so any container can start on any single docker swarm node and fail between nodes and see the data it needs to
  - enable safe replicated shared volume across all nodes that allow state to be replicated and accessible from all nodes and allows for use of datatbases like mariadb which will corrupt if placed on NFS or CIFS/SMB shares across the network
  - make it easy to backup with my synology (this model enabled me to easily backup using active backup for business)

## current state 8/24/2026
- all stacks now deploy [from git](gitops-with-portainer.md), not the portainer web editor
    - each stack watches its own branch, so a commit only redeploys the stacks it touched
    - point them all at `main` and every commit redeploys everything, don't do that
- [passwords are out of the service specs](../secrets/index.md). they were env vars, so anything that could reach the docker API could read them, and my docker socket proxy on the LAN had no authentication. both fixed
- watchtower and shepherd are gone, replaced by [renovate](image-updates-renovate.md) opening PRs against the compose files
- also retired: traefik, NPM does the job
- two stacks had been broken for a while and nobody noticed, because nothing was checking
- new: [troubleshooting notes](troubleshooting.md). one covers why a container can't reach a macvlan container on the same host, which made my uptime monitoring wrong for a long time

## current state 4/14/2025
- VMs updated to debian bookworm using apt, and latest docker version
- still love portainer - use it so much i paid for the education/home version
- in the middle of migrating to virtioFS for bind mounmts, backed by my cephFS cluster, as my first attempt to migrate away from glusterFS
    - goal: get rid of the gluster service and vdisks
- found swarm is very bad at knowing if a volume is truly unsed or not
    - this broke badly with glusterFS
    - i removed all the volumes marked as unused created by the plugin - seems when you delete the volume using docker / portainer it deleted the volumen *AND* the data in them 
    - this seems to be because the volume is linked via inodes to the gluster storage it deleted the data on the node were it was marked unused and this deletions was replicated to all other nodes - EEK.  
    - I had to do full restore of alll 3 VM nodes from my PBS backup.  This worked surprisingy well.

## current state 9/30/2024
- all still working
- all running now on top of my proxmox cluster (see here)
- only issue is fragile GlusťerFS plugin that needs me to re-enable it when the inteface on the hosts becomes available (e.g upgrading my unifi switch)

## current state 8/26/2023
  - all seems to be functioning nearly a year layte
  - I switched fully from native nginx container to NPM
  - i elimnated NFS and iSCSI and moved all containers with state to running on GlusterFS inlcuding things with databases like wordpress
  - i plan to move the VMs from Hyper-V to my new [proxmox cluster](../proxmox/index.md)

Update as of 2026.09.24: the architecture and design below are from the original 2022 build. gluster has since been replaced by cephFS over virtioFS, and docker comes from docker's own repo.

## Architecture

![image](../assets/img/c0ff2782ab90.jpeg)


### Design Assumptions
- I wanted to continue to use docker, docker-compose, docker swarm & portainer due to existing skills
- I have no interest at this time in k8s (i don't use it at work and never will)
- Start simple, even if that means i do what i shouldn't (this is just a home network)
- This is small, the containers include (nginx reverse proxy, oauth2-proxy, wordpress site + database, mqtt, cloudflare ddns) so bear that in mind, this isn't designed for super throuput or scale - its designed for some resilliency.
- I want to deploy all services (containers) with stack templates and possibly contribute back to portainer template repo
- The clustered file system must support databases on it (like mariadb)

### Design Decisions
- Debian for my docker host VMs - i seem to gel with debian and it (and other debian derivatives) seems to play nice with most contaniners
- I will only use package versions included in the debian distri (bullseye stable)
- I chosee glusterfs as my clustered, replicated file system
- Gluster volumes will be deployed in dispersed mode
- I mapped seperate VHDs into the docker hosts one for OS and one for gluster - this is to prevent risk of infinite boot loops
- my gluster service will be installed on the docker host VMs.  Best practice dicates they should be seperate VMs for scale.  But as all VMs share the same host CPU this really gives no benefit. If this turns out to be bad decision i will change.
- I wont tear down my current NFS and iSCSI mapped volumes (not shown) until glusterfs has been shown to run ok and survive reboots etc

## A note on docker swarm and state (assume you know docker already)
Docker containers are ephemeral and generally loose all their data when they are stopped. For most docker containers there is some level of confguration state you need to pass to the container (variable, file, folders of data). Simillarly many containers want to persist data state (databases, files etc)

On a single node docker most people map a directory or file on the host into the container as a volumen or bind mount.
We also see the following more advanced techniques used:

1. mount a shared CIFS or NFS volume at bootime on the docker hosts
2. defining a CIFS volume and mapping it into the container at runtime (this avoids editing fstab on the host)
3. same as aove but with NFS
4. using configs - if you have just a single, readi only, confg file that needs to  be read this can be defined.

In a swarm where you want a container to run on any node you need to find a way to make the data available on all nodes in a safe effective way.

If you have a simple container that only needs environment variables to be cofigure you can do that directly when you deploy the portainer template as a portaineer stack.  See this [cloudflare dynamic dns updater](../apps/cloudflare-ddns.md) as an example.

- Only #4 offers a safe way to make this happen (the 'config' is available to all nodes) - but this is super restrictive and doesn't help with containers that need to store more state and read/write that state. See this [mosquitto mqtt example](../apps/mosquitto-mqtt.md)
- \#1 this can work and you can mount the shares to multiple nodes via fstab.  Typically databases cannot be placed on these shares and will ultimately corrupt.  You do have to be careful to only have one container writing to any given file to avoid potentials issues.
- \#2 and #3 - thishas the advantage of not being generall mounted to the host OS, but mount on demand by the container, this reduced all the tedious mucking about is ~~hyperspace~~ fstab.  You do need to use the volumes UI in portaine for this.

and for nost folks NFS/CIFS shares are not replicated for high availability.

This is why in this architecture i have chose to see if I can overcome these limitations uings glusterfs.
