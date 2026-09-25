---
title: "Install docker on debian the easy way"
source_gist: https://gist.github.com/scyto/83bc728e47afeb21bf42c8a96fe6ccfd
---

# Install docker on debian the easy way

This is the easiest way to install docker and docker compose on debian.

Better yet docker updates can be done by rerunning the script mentioned or using apt upgrade etc

Assumes you followed [Debian VM Install Instructions](debian-vm-install.md)

## Install Docker
Login as yourself
```
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl enable docker
sudo systemctl start docker
```
No really thats it. Note the latest version of the script automatically installs the docker compose plugin. so no need to install python or old docker-compose python app.

## Let your user run docker without sudo

The install script does not add you to the `docker` group. Until you add
yourself, `docker ps` fails with a permission error on `/var/run/docker.sock`:

```
sudo usermod -aG docker $USER
```

Then log out and back in. Group membership only applies to new login sessions,
so your current shell keeps failing until you reconnect.

```
id -nG        # docker should now be listed
docker ps     # should work with no sudo
```

Use `-aG`. Without `-a`, usermod replaces your supplementary groups, `sudo`
included.

### This is required if you manage the host remotely

A remote Docker context like this one runs `docker system dial-stdio` on the
target over SSH:

```
docker context create mynode --docker host=ssh://user@mynode
```

There is no way to prefix that with `sudo`, so a remote context cannot drive a
host where docker needs sudo. If you plan to manage the node from your
workstation, this step is mandatory.

The same applies to anything else that talks to the daemon over SSH, including
`DOCKER_HOST=ssh://...`.

### Know what you are granting

Membership of the `docker` group is equivalent to root on that host. Anyone in
it can start a container that mounts the host filesystem and has full access to
it. That is how the Docker socket works, and it is why the group is not
populated for you.

On a machine where you already have full `sudo`, this grants nothing new: it
only removes a password prompt.

## If your stacks keep their data on a shared mount

Docker doesn't know it needs that mount. On the swarm VMs I make it wait for the
mount and refuse to start against an empty one, see
[make docker wait for the mount](../../proxmox/cephfs-start-guards.md#docker-data-guard).
Set it up once the data is on the mount, because the check fails on an empty
one.
