---
title: "IPv6"
---

# ipv6, routed, no nat

dual stack on the docker hosts with containers holding real addresses. docker 28
defaults to nat66 on bridge networks; this replaces that with routing.

docker never reads router advertisements for container networks — no slaac, no
dhcpv6-pd, no ndp proxy. addresses come from docker's own ipam, so the prefix
has to be routed to the host by the router or nothing outside the host can
answer a container.

## addressing

a /56 from the isp, one /64 per purpose per host.

| prefix | purpose | next hop |
| --- | --- | --- |
| `2001:db8:1000:1::/64` | lan, hosts at `2001:db8:1000:1::41` `:42` `:43` | on-link |
| `2001:db8:1000:d1::/64` | docker01 bridge networks | `2001:db8:1000:1::41` |
| `2001:db8:1000:d2::/64` | docker02 bridge networks | `2001:db8:1000:1::42` |
| `2001:db8:1000:d3::/64` | docker03 bridge networks | `2001:db8:1000:1::43` |
| `2001:db8:1000:e1::/64` | docker01 `docker_gwbridge` | `2001:db8:1000:1::41` |
| `2001:db8:1000:e2::/64` | docker02 `docker_gwbridge` | `2001:db8:1000:1::42` |
| `2001:db8:1000:e3::/64` | docker03 `docker_gwbridge` | `2001:db8:1000:1::43` |

- a /64 per host per bridge type, not per network. networks take /80s out of the
  host's /64, so adding one needs no router change
- the six static routes go on the router before anything below. without them
  containers reach nothing and the failure looks like a docker problem

## 1. host interface

`/etc/network/interfaces`, per host:

```
iface eth0 inet6 static
  accept_ra 0
  address 2001:db8:1000:1::42
  netmask 64
  gateway 2001:db8:1000:1::1
```

- options are `key value`, never `key = value`. an option written `accept_ra = 2`
  is dropped without an error, so the host runs on the kernel default while the
  file claims otherwise
- the `gateway` line is what installs the default route, so router
  advertisements are not needed here
- `accept_ra 0` says so explicitly. at `2` the host also takes an ra-learned
  default route at `pref high`, which outranks the static one, and a slaac
  address with a lifetime alongside the static address
- source selection can then pick the slaac address for outbound traffic, so the
  host talks from an address that is not the one in dns, the firewall rules or
  the portainer environment
- these hosts forward ipv6 for the container prefixes, and a forwarding host
  ignores ras unless `accept_ra` is `2`. so ras only arrive if you ask for them,
  and there is no reason to ask on a host whose addressing is static

### check the stanza before rebooting

```
sudo ifup --no-act --force -v eth0
```

this prints the commands the stanza will run at boot without running them. a
parsed option appears as its sysctl:

```
sysctl -q -e -w net.ipv6.conf.eth0.accept_ra=0
```

- no such line means the option was not parsed
- `--force` is required. without it ifup exits with "interface eth0 already
  configured" and checks nothing

## 2. daemon

`/etc/docker/daemon.json`, identical on every host:

```json
{
  "experimental": true,
  "ip6tables": true,
  "default-network-opts": {
    "bridge": {
      "com.docker.network.bridge.gateway_mode_ipv6": "routed"
    }
  }
}
```

- `gateway_mode_ipv6: routed` drops the masquerade rule and forwards the
  container's own source address. the default is `nat`
- `default-network-opts` reaches user-defined networks only. the default bridge
  is configured from daemon flags and ignores it, so `docker0` cannot be put in
  routed mode and would keep a nat66 rule — it gets no ipv6 at all here, which is
  why there is no `ipv6` or `fixed-cidr-v6` key
- nothing is attached to `docker0` on these hosts; stacks all use their own
  networks
- restart the daemon to apply: `sudo systemctl restart docker`

after a prefix change, clear the old address off the bridge:

```
sudo ip -6 addr flush dev docker0
```

- removing ipv6 from a bridge leaves the address on the interface, and the
  kernel route it created keeps black-holing that prefix on every host that
  still has it

## 3. stacks on a standalone host

this section is for bridge networks, which is what compose creates on a single
host. **swarm stacks need none of it** — their networks are overlays and their
ipv6 comes from `docker_gwbridge`, see below.

nothing enables ipv6 for a stack globally. `"ipv6": true` covers `docker0` only,
and `-o com.docker.network.bridge.enable_ipv6=true` is accepted and ignored. each
network opts in:

```yaml
networks:
  default:
    enable_ipv6: true
    ipam:
      config:
        - subnet: 2001:db8:1000:d2:10::/80
```

- the subnet comes out of that host's own /64, since the router points the
  prefix at one host. stacks on a standalone host live at `stacks/<host>/`
  already, so this adds no constraint
- routed mode is inherited from the daemon; no `driver_opts` needed
- without an explicit subnet docker assigns a ula, which is not routable and has
  no path out under routed mode

## 4. swarm

swarm tasks do not use either bridge above, and a swarm stack file needs no ipv6
in it. every task on an overlay network gets a second interface on
`docker_gwbridge`, which swarm creates ipv4 only. it has to be replaced per node.

a task therefore takes its ipv6 from whichever node it lands on — `e1`, `e2` or
`e3` — and the address changes when it moves. nothing about this pins a service
to a host. the overlays themselves stay ipv4 only.

**publishing means something different under routed mode.** there is no host
port mapping for ipv6 — `docker port` shows `[::]:` with no port, which is
expected. what a published port does is open the **container's own address**:

```
-A DOCKER -d 2001:db8:1000:d1:5::2/128 ! -i br-4f7a4b187179 -p tcp --dport 80 -j ACCEPT
```

so a container answers on its own address at its published ports, from anywhere
the router routes, and the host address is not involved. unpublished ports stay
closed: the chain ends in a `DROP`.

that applies to swarm tasks too, on the gwbridge address:

| how a service publishes | ipv6 |
| --- | --- |
| host mode | works, at the task's `eN::` address on the node running it |
| ingress | does not work |

the ingress sandbox does carry a gwbridge address with an accept rule for every
published port, but nothing behind it handles v6: in
`daemon/libnetwork/service_linux.go` the ipvs service is built with
`AddressFamily: nl.FAMILY_V4`, and `configureFWMark` and `addRedirectRules` both
carry `// TODO IPv6 support` and call `iptables.GetIptable(iptables.IPv4)`.

on the **host** address, no published port answers over ipv6 in either mode. on
28.x the daemon bound the v6 port anyway and connections hung after the
handshake — [moby#53091](https://github.com/moby/moby/issues/53091), present
since 26.x. [moby#53118](https://github.com/moby/moby/pull/53118) in 29.8.0
stopped reserving that port, so it now refuses immediately instead.

these addresses come from ipam per node, so a task's address changes when it
moves or is recreated. treat them as discovered, not configured.

do not put an ipv6 subnet on the ingress network to try to fix this. the load
balancer is ipv4 in code regardless, and on newer engines an ingress network
carrying a v6 subnet fails to come up on workers.

publishing to `::` does work, and is per-port:

```
docker run -d -p "[::]:8099:80" nginx:alpine
```

- binds `[::]:8099` and answers over ipv6 from the lan
- it is v6 **only** — the same container is unreachable on the host's ipv4
  address until a second `-p 0.0.0.0:8099:80` is added
- in host mode a compose port entry takes `host_ip: "::"`, so a dual-stack
  service needs two entries
- a host-mode port answers only on the node running the task, with no routing
  mesh

what does answer over ipv6 without any of that is the container's own address on
a routed bridge network, from anywhere the router routes.

per node, one at a time:

```
docker node update --availability drain <node>
```

```
for e in $(docker network inspect docker_gwbridge --format '{{range $k,$v := .Containers}}{{$v.Name}} {{end}}'); do docker network disconnect -f docker_gwbridge "$e"; done; docker network rm docker_gwbridge
```

```
docker network create --ipv6 \
  --subnet 172.18.0.0/16 --gateway 172.18.0.1 \
  --subnet 2001:db8:1000:e2::/64 --gateway 2001:db8:1000:e2::1 \
  -o com.docker.network.bridge.name=docker_gwbridge \
  -o com.docker.network.bridge.enable_icc=false \
  -o com.docker.network.bridge.enable_ip_masquerade=true \
  -o com.docker.network.bridge.gateway_mode_ipv6=routed \
  docker_gwbridge
```

```
sudo systemctl restart docker
docker node update --availability active <node>
```

- **the restart is required.** the removal needs `gateway_ingress-sbox`
  force-disconnected, which destroys the ingress sandbox, and docker only
  rebuilds it when the daemon restarts. until then every ingress-published port
  on that node is dead while the node reports healthy — tasks running, services
  converged, nothing in the logs
- keep the v4 subnet and `enable_icc` / `enable_ip_masquerade` exactly as they
  were. v4 keeps its nat
- drain first or the removal fails with "has active endpoints"
- check a published port on the node before moving to the next one, not just
  container egress

a task then looks like this — `eth0` on the overlay, `eth1` on the gwbridge:

```
eth0  10.0.9.9/24
eth1  172.18.0.6/16
eth1  2001:db8:1000:e2::6/64
      default via 2001:db8:1000:e2::1 dev eth1
```

## verify

```
sudo ip6tables -t nat -S POSTROUTING | grep -c MASQUERADE
```

- zero. anything else means a network is still in nat mode

```
docker run --rm --network <v6-network> alpine:3 ping6 -c2 <public-v6-address>
```

- egress. to prove the source address survives, watch it arrive on another lan
  host: `sudo tcpdump -ni any icmp6` should show the container's address, not the
  host's

## exposure

published ports are globally routable addresses now; nat is no longer hiding
anything behind the host. docker still defaults to deny — the `DOCKER` chain
ends in `! -i docker_gwbridge -o docker_gwbridge -j DROP` and only published
ports get an accept — but the router's ipv6 wan-in policy is now what stands
between the internet and anything published.
