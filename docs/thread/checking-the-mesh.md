---
title: "Checking the Mesh"
---

# checking the mesh

how i check the two border routers are one mesh, what each one publishes, and
what a failover looks like. the examples use my ESP's name, `esp-ot-br-33f0`,
which comes from step 4 of
[build and flash it](esp-border-router.md#build-and-flash-it).

## the ESP's API

```
curl -s http://esp-ot-br-33f0.local/topology
```

it returns one entry per router, with its extended address, `Rloc16` and links.
the router ID is `Rloc16` divided by 1024. a child's `Rloc16` has a non zero
remainder. `LeaderData.PartitionId` should be the same in every entry.

## mDNS

every border router announces `_meshcop._udp`:

```
dns-sd -B _meshcop._udp local.
dns-sd -L esp-ot-br-33f0 _meshcop._udp local.
```

`dns-sd` is macOS. on Linux the same two are `avahi-browse _meshcop._udp` and
`avahi-browse -r _meshcop._udp`. most TXT values are binary, so both print them
garbled.

| key | what it is |
| --- | --- |
| `nn` | network name |
| `xp` | extended PAN ID. Home Assistant groups border routers into a network by this |
| `pt` | partition ID, a random number picked by the leader and only announced once attached. the same `pt` on two border routers means one mesh |
| `sb` | state bitmap. bits 0 to 2 connection mode, 3 to 4 Thread interface (2 is active), 7 backbone router active, 8 backbone router primary, 9 to 10 role (1 child, 2 router, 3 leader), 11 ePSKc supported |
| `omr` | the routable prefix the border router favours for Thread devices |
| `at` | active dataset timestamp |
| `tv`, `vn`, `mn` | Thread version, vendor, model |

my ESP's firmware fills `sb`, `omr` and `at` differently from OpenThread's own
border router: no role bits, and its own prefix in `omr`. i read its role from the
REST API, not from mDNS.

/// details | decode the TXT records with python
    type: example

no packages needed. it sends one mDNS query for each instance name and prints
the fields above.

```python
import socket, struct, sys, time

def qname(n):
    return b"".join(bytes([len(p)]) + p.encode() for p in n.split(".")) + b"\0"

def read_name(buf, off):
    end = None
    while buf[off]:
        if buf[off] & 0xC0 == 0xC0:
            end = end or off + 2
            off = ((buf[off] & 0x3F) << 8) | buf[off + 1]
        else:
            off += 1 + buf[off]
    return end or off + 1

def txt(instance):
    name = f"{instance}._meshcop._udp.local"
    pkt = struct.pack(">6H", 0, 0, 1, 0, 0, 0) + qname(name) + struct.pack(">HH", 16, 0x8001)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    deadline = time.time() + 3
    while time.time() < deadline:
        s.sendto(pkt, ("224.0.0.251", 5353))
        try:
            buf, _ = s.recvfrom(9000)
        except socket.timeout:
            continue
        counts = struct.unpack(">6H", buf[:12])
        off = 12
        for _ in range(counts[2]):
            off = read_name(buf, off) + 4
        for _ in range(sum(counts[3:])):
            off = read_name(buf, off)
            rtype, _, _, rlen = struct.unpack(">HHIH", buf[off:off + 10])
            rdata = buf[off + 10:off + 10 + rlen]
            off += 10 + rlen
            if rtype == 16 and b"xp=" in rdata:
                kv, i = {}, 0
                while i < len(rdata):
                    k, _, v = rdata[i + 1:i + 1 + rdata[i]].partition(b"=")
                    kv[k.decode()] = v
                    i += 1 + rdata[i]
                return kv

for inst in sys.argv[1:]:
    kv = txt(inst) or {}
    print(inst)
    for k in ("nn", "xp", "pt", "sb", "omr", "at", "tv", "vn", "mn"):
        if k in kv:
            v = kv[k]
            if k in ("nn", "tv", "vn", "mn"):
                v = v.decode(errors="replace")
            elif k == "omr":
                v = f"{v[1:].hex()} /{v[0]}"
            elif k in ("pt", "sb"):
                v = f"{int.from_bytes(v, 'big')} (0x{v.hex()})"
            else:
                v = v.hex()
            print(f"  {k} = {v}")
```

```
python3 meshcop.py esp-ot-br-33f0 "Home Assistant OpenThread Border Router #XXXX"
```

the instance names are the ones `dns-sd -B` lists.

///

## what each border router publishes

this comes from the network data. on the ESP's USB console, run:

```
ot netdata show
ot bbr
```

each entry includes the hex `Rloc16` of the router that published it (`a400` is
router 41, `3800` router 14). `::/0` is a default route, a route with `n` in
its flags is a NAT64 prefix, service `5d` is an SRP server and service `01` is a
backbone router. `ot bbr` names the primary.

this is what mine have published since the [failover](#watching-a-failover):

| | app | ESP |
| --- | --- | --- |
| default route off the mesh | yes | yes |
| SRP server, where Thread devices register | yes | yes |
| routable (OMR) prefix | uses the ESP's | publishes it |
| backbone router | standby | primary |
| NAT64 prefix | no | yes |

one border router at a time holds the prefix and the primary backbone router.
before the failover the app had both, and they did not move back when it
returned. a border router only publishes its own prefix when the network has
none, or only a lower preference one. that puts every router on one prefix
without any setting.

Thread devices reach IPv4 only addresses through the ESP either way.

## watching a failover

the ESP's REST API is enough to watch what happens when the app goes away, with
no USB.

1. turn the [automation](index.md#the-automation) off, then stop the app
2. watch the routers' addresses and the ESP's own

    ```
    curl -s http://esp-ot-br-33f0.local/diagnostics | jq -c '.[] | {router: (.Rloc16 / 1024 | floor), addresses: .IP6AddressList}'
    curl -s http://esp-ot-br-33f0.local/ipaddr | jq -c '.result[] | {address, preferred}'
    ```

    - an address ending `0:ff:fe00:fc38` is the primary backbone router's,
      `fc00` the leader's, `fc10` upwards are services
    - an address outside the mesh-local prefix and `fe80::` is in the routable
      prefix
    - `"preferred": false` is a deprecated address. the web UI dashboard shows
      the same list
    - in mDNS, bit 8 of `sb` is set on the primary backbone router, see
      [mDNS](#mdns)

3. turn the automation back on. it starts the app again

this is what mine did:

| after stopping the app | |
| --- | --- |
| about 5 minutes | the app's router dropped out. the ESP became primary backbone router and published its own prefix |
| straight after | addresses in the old prefix deprecated |
| 5 minutes later | those addresses removed. OpenThread's default is 300 seconds |
| automation back on | the app rejoined as the same router, standby, on the ESP's prefix |
