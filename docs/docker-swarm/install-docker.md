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
