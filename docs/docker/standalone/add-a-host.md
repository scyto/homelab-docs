---
title: "Add a Host"
---

# add a standalone host

1. install docker. the pi uses docker's own apt repo, truenas and synology ship it
2. start the agent:

    ```
    docker run -d -p 9001:9001 --name portainer_agent --restart=always \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /var/lib/docker/volumes:/var/lib/docker/volumes \
      -v /:/host \
      portainer/agent:lts
    ```

    - keep the agent on the same version as the server
    - on synology, docker's data is under `/volume1/@docker`, so mount `/volume1/@docker/volumes` there instead, see [syn02](syn02.md)
    - on truenas the agent runs as a truenas custom app instead, see [truenas1](truenas1.md)

3. in portainer, add a docker standalone environment using the agent, at `<host>:9001`
4. add its stacks from git as on the swarm: reference `refs/heads/deploy/<host>/<stack>`, compose path `stacks/<host>/<stack>/compose.yml`
