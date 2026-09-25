---
title: "Thread Radio"
---

# thread radio over the network

OpenThread does not run on the pi. it runs as Home Assistant's OpenThread Border
Router app on the Home Assistant VM, and the radio stays here. `ser2net` exposes
the SkyConnect on TCP port 8000, and the app's network device setting points at
`192.168.1.96:8000`. the app connects with socat and treats the socket as its
serial port.

i ran the border router here twice, in containers, and went back to this both
times. a border router here and the app cannot both use the radio at once, so it
is one or the other. the history, the network as a whole, the second border
router, and getting the app running again after the pi has been off are on the
[thread](../thread/index.md) page.

ser2net reads `/docker-data/ser2net/data/ser2net.yaml`, which the
[compose](stacks.md#ser2net) binds in. the file lives on the pi, not in git:

//// details | ser2net.yaml, 8 lines
    type: example
    open: true

``` { .yaml linenums="1" }
%YAML 1.1
---
connection: &skyconnect
  accepter: tcp,8000
  connector: serialdev,/dev/ttyUSB1,460800n81,local,rtscts
  options:
    kickolduser: true
    remaddr: 192.168.1.63,0;2001:db8:1000:1::63,0
```

////

| line | why |
| --- | --- |
| `serialdev,/dev/ttyUSB1` | the compose maps the SkyConnect's by-id path to `/dev/ttyUSB1` inside the container |
| `460800n81` | the speed the app runs the radio at |
| `local` | ignore the modem control lines |
| `rtscts` | hardware flow control between ser2net and the radio. the app's flow control setting (on, its default) has no effect over the network socket, so flow control is set here |
| `kickolduser: true` | ser2net takes one connection per port by default. without this, a half-open session left by a VM or app restart blocks the reconnect |
| `remaddr` | only Home Assistant can connect, from its IPv4 or IPv6 address and any source port (`,0`). otherwise anything on the LAN can talk to the thread radio |

i leave the banner off. ser2net can send one when a client connects, and that is
text arriving in front of a binary protocol. mine used to, and it only worked
because the framing throws away junk before the first frame.

ser2net reads the file at start, so after a change restart `ser2net` first, then
the app.

## checking it

ser2net logs only errors: a config it cannot load, a device it cannot open, and
read or write failures. the image already runs it with `-d`, which sends those
to `docker logs`. a working connection logs nothing, so an empty log is the good
case.

```
sudo ss -tnp | grep ser2net
```

you should see one `ESTAB` line from Home Assistant's address. an IPv4 client
shows with a `::ffff:` prefix in front of its address, because ser2net listens
on IPv4 and IPv6 on the same socket.

the app's log should show the thread role:

```text
Mle-----------: Role detached -> router
```

the ESP board holds the primary backbone router (see
[watching a failover](../thread/checking-the-mesh.md#watching-a-failover)), so
the app runs as the standby and does not log `Backbone Router becomes Primary!`.

`remaddr` has to match the source address Home Assistant connects from, which
its OS picks. give it a fixed address, and check with `ss` rather than assuming.

i have not tested how `remaddr` interacts with `kickolduser`, so i do not test
the restriction by connecting from another machine while the app is connected.

