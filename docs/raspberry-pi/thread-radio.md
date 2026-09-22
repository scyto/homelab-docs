---
title: "Thread Radio"
---

# thread radio over the network

OpenThread does not run on the pi. it runs as Home Assistant's OpenThread Border
Router add-on, on the Home Assistant VM, and the radio stays here: `ser2net`
exposes the SkyConnect on TCP port 8000 and the add-on's network device setting
points at `192.168.1.96:8000`. the add-on connects with socat and treats the
socket as its serial port.

why not run the border router here: i did, twice, in containers, and went back
to this both times. the history, the network as a whole, the second border
router, and getting the add-on running again after the pi has been off are on
the [thread](../thread/index.md) page. both cannot use the radio at once, so it is
one or the other.

`/docker-data/ser2net/data/ser2net.yaml`:

```yaml
%YAML 1.1
---
connection: &skyconnect
  accepter: tcp,8000
  connector: serialdev,/dev/ttyUSB1,460800n81,local,rtscts
  options:
    kickolduser: true
    remaddr: 192.168.1.63,0;2001:db8:1000:1::63,0
```

| line | why |
| --- | --- |
| `serialdev,/dev/ttyUSB1` | the compose maps the SkyConnect's by-id path to `/dev/ttyUSB1` inside the container |
| `460800n81` | the speed the add-on runs the radio at |
| `local` | ignore the modem control lines |
| `rtscts` | hardware flow control between ser2net and the radio. the add-on asks for flow control, but on a network socket its own setting does nothing, this is the link where it counts |
| `kickolduser: true` | ser2net takes one connection per port by default. without this, a half-open session left by a VM or add-on restart blocks the reconnect |
| `remaddr` | only Home Assistant can connect, by its IPv4 or IPv6 address, any source port (`,0`). otherwise anything on the LAN can talk to the thread radio |

**no banner.** ser2net can send a banner when a client connects, and mine used
to. that is text arriving in front of a binary protocol. it only worked because
the framing throws away junk before the first frame.

ser2net reads the file at start, so after a change restart `ser2net` first, then
the add-on.

## is it working

ser2net logs errors only, a config it cannot load, a device it cannot open,
read or write failures. the image already runs it with `-d`, which sends those
to `docker logs`. a working connection logs nothing, so an empty log is the good
case.

```
sudo ss -tnp | grep ser2net
```

one `ESTAB` line from Home Assistant's address. an IPv4 client shows with a
`::ffff:` prefix in front of its address, because ser2net listens on IPv4 and
IPv6 on the same socket.

and in the add-on's log, the thread role:

```
Mle-----------: Role detached -> router
BackboneAgent: Backbone Router becomes Primary!
```

`remaddr` has to match the address Home Assistant connects **from**, which its
OS picks. give it a fixed address, and check with `ss` rather than assuming.

i have not tested how `remaddr` interacts with `kickolduser`, so i do not test
the restriction by connecting from another machine while the add-on is connected.

