---
title: "bootstrap docker swarm"
source_gist: https://gist.github.com/scyto/0a9b71f35d375d4dba6c1c5aba0045f3
---

# bootstrap docker swarm

i like using docker swarm for home labs

assumes you [installed docker like this](install-docker.md) 

## Initialize Swarm on first docker node (management node)

```
sudo docker swarm init
```
it will produced output something like this
```
docker swarm join --token <some-very-long-token> 192.168.1.41:2377
```
make sure you copy and keep this command as you will run it on all your other nodes
(the IP address should match the IP of this management node, if it doesn't you need to troubleshoot networking).


## Initialize worker nodes
On each worker node run the command from the last step

```
sudo docker swarm join --token <some-very-long-token> 192.168.1.41:2377
```
the IP is the IP of the management node and doesn't need to be changed as you run this on each node.

thats it you should now have a fully functioning swarm
