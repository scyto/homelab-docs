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

The install script does **not** add you to the `docker` group, so `docker ps`
fails with a permission error on `/var/run/docker.sock` until you do:

```
sudo usermod -aG docker $USER
```

Log out and back in — group membership only applies to new login sessions, so
your current shell will keep failing until you reconnect.

```
id -nG        # docker should now be listed
docker ps     # should work with no sudo
```

Note `-aG` and not `-G`. Without the `-a` this **replaces** all your
supplementary groups rather than adding one, which removes you from `sudo` and
costs you admin on the box. Same command, one character, very different day.

### This is required if you manage the host remotely

Not just convenience. A remote Docker context:

```
docker context create mynode --docker host=ssh://user@mynode
```

works by running `docker system dial-stdio` on the target over SSH. There is no
way to prefix that with `sudo`, so a host where docker needs sudo cannot be
driven by a remote context at all. If you plan to manage the node from your
workstation rather than by SSHing in and typing commands, this step is
mandatory.

The same applies to anything else that talks to the daemon over SSH, including
`DOCKER_HOST=ssh://...`.

### Know what you are granting

Membership of the `docker` group is **equivalent to root on that host**. Anyone
in it can start a container that mounts the host filesystem and walk out with
full access. That is inherent to how the Docker socket works, not a
misconfiguration, and it is why the group is not populated for you.

On a machine where you already have full `sudo`, this grants nothing new — it
only removes a password prompt. On a shared machine, think harder.

## If your stacks keep their data on a shared mount

Docker doesn't know it needs that mount. On the swarm VMs I make it wait for the
mount and refuse to start against an empty one, see
[make docker wait for the mount](../proxmox/cephfs-virtiofs-passthrough.md#docker-data-guard).
Do that once the mount exists, the check fails without it.
