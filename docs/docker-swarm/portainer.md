---
title: "Installing Portainer on a swarm"
source_gist: https://gist.github.com/scyto/a57d63a3b905b24e9eb25618848c8e80
---

# Installing Portainer on a swarm

This is how to install portainer on the swarm [you created using this gist](configure-swarm.md)
note this should work on non-swarm installs too!

## Setup Portainer
Download the portain stack yaml that will do this for you (you will need to change this to use the latest version, this is an example, read the portainer docs)

```
curl -L https://downloads.portainer.io/ce2-17/portainer-agent-stack.yml -o portainer-agent-stack.yml
```

now run it 

```
sudo docker stack deploy -c portainer-agent-stack.yml portainer
```

this will create a single portainer container that runs on the management node and deploy the agent to all worker nodes, once complete you can now access portainer at http://docker-host-ip:9000 and define your admin users etc

You now have a fully function docker swarm with portainer and can deploy containers, stacks or templates.   
  
How to use portainer is beyond the scope of this gist
  

[This is the portainer install doc at time of writing for reference](https://docs.portainer.io/start/install-ce/server/swarm/linux) but the instructions above will work just fine
