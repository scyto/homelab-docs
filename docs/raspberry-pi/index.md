---
title: "Raspberry Pi: pi-zwave01"
---

# raspberry pi: pi-zwave01

a Raspberry Pi 4 Model B that holds the USB radios for home automation, keeps
time from a GPS and serves it to the LAN, and shows its status on a small OLED. it is a standalone docker
host, not part of the swarm, and its stacks deploy from
[git](../docker-swarm/gitops-with-portainer.md) like everything else.

everything here was read off the running pi, so it describes this machine rather
than a recipe. i am turning it into a rebuild script, see
[backups](../backups/pi-host-backup.md) for how the data side is covered.

## OS

| | |
| --- | --- |
| hardware | Raspberry Pi 4 Model B Rev 1.5 |
| OS | Debian 13 (trixie), 64 bit, with the Raspberry Pi archive for the kernel and firmware |
| installed with | Raspberry Pi Imager, which sets up first boot through cloud-init |

two things cloud-init keeps owning after first boot, worth knowing before you
edit them:

- `/etc/hosts` is regenerated from `/etc/cloud/templates/hosts.debian.tmpl`
  (`manage_etc_hosts` is on)
- `/etc/ssh/sshd_config.d/50-cloud-init.conf` sets `PasswordAuthentication yes`

## boot config

the lines in `/boot/firmware/config.txt` that matter for this pi:

```
dtparam=i2c_arm=on              # i2c for the OLED
enable_uart=1                   # serial port for the GPS
dtoverlay=disable-bt            # gives the GPS the full UART instead of the mini UART
dtoverlay=pps-gpio,gpiopin=4    # the GPS PPS line on GPIO 4 becomes /dev/pps0
```

and `/boot/firmware/cmdline.txt` has no `console=serial0`, so the kernel does not
put a login console on the port the GPS uses.

with that, `/dev/serial0` points at `/dev/ttyAMA0` and `/dev/pps0` exists.

## network

NetworkManager, one ethernet profile with static addresses,
`/etc/NetworkManager/system-connections/LAN.nmconnection`:

```ini
[connection]
id=LAN
type=ethernet
interface-name=eth0

[ipv4]
method=manual
address1=192.168.1.96/24
gateway=192.168.1.1
dns=192.168.1.35;192.168.1.36;
dns-search=yourdomain.com;

[ipv6]
method=manual
address1=2001:db8:1000:1::96/64
gateway=2001:db8:1000:1::1
dns=2001:db8:1000:1::35;2001:db8:1000:1::36;
dns-search=yourdomain.com;
```

the DNS servers are my two internal DNS servers, not the AdGuards.

## docker

Docker CE from Docker's own apt repository, the same setup
[get.docker.com](../docker-swarm/install-docker.md) creates:

```
/etc/apt/keyrings/docker.asc
/etc/apt/sources.list.d/docker.list:
  deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable
```

no `/etc/docker/daemon.json`, and `containerd`'s config is the package default
(`disabled_plugins = ["cri"]`). nothing tuned.

### portainer agent

started by hand once, not from git, because it is what lets Portainer deploy
everything else here:

```
docker run -d -p 9001:9001 --name portainer_agent --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  -v /:/host \
  portainer/agent:<version>
```

keep `<version>` matched to your Portainer server.

## radios and stacks

the USB radios are passed to containers by their `/dev/serial/by-id/` names, so
they land on the right device whatever order they enumerate in.

| radio | by-id name starts | used by |
| --- | --- | --- |
| Zooz 800 Z-Wave stick | `usb-Zooz_800_Z-Wave_Stick_` | `zwave-js-ui` |
| Nabu Casa SkyConnect | `usb-Nabu_Casa_SkyConnect_v1.0_` | `ser2net`, for Home Assistant's OpenThread add-on, see [below](#thread-radio-over-the-network) |
| Sonoff Zigbee 3.0 USB Dongle Plus | `usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_` | `zigbee2mqtt` stack (in git, not running on this pi now) |

### stacks, deployed from git

three stacks are defined for this pi and two of them are deployed, from git by
Portainer through the [portainer agent](#portainer-agent) above, exactly as the
swarm's are. see [moving stacks from the web editor to
git](../docker-swarm/gitops-with-portainer.md) for the mechanism.

| stack | radio | network | ports | data |
| --- | --- | --- | --- | --- |
| `zwave-js-ui` | Zooz 800 | its own bridge | `80` to the UI on 8091, `3000` for the Z-Wave JS websocket | `/docker-data/zwavejs2mqtt/store` |
| `ser2net` | SkyConnect | host | `8000` | `/docker-data/ser2net/data/ser2net.yaml` |
| `zigbee2mqtt`, not deployed | Sonoff dongle | bridge | `8080` | `/docker-data/zigbee2mqtt/data` |

- each stack polls **its own** branch, `deploy/pi-zwave01/<stack>`, every five
  minutes. `main` is not deployed, so a commit only reaches the stack whose
  directory it changed
- a **stopped** stack does not poll at all. it stays on the commit it was last
  deployed from, however far behind that ends up, while looking fine in
  Portainer's stack list
- this is a standalone docker host, not a swarm, so the compose keys swarm
  ignores all work here: `container_name`, `restart`, `devices`, host networking
- `zwave-js-ui` also mounts `/etc/localtime` and `/etc/timezone` read-only so its
  logs use the pi's time zone
- `ser2net`'s healthcheck looks for an established connection on port `8000`, so
  healthy means a client is attached. unhealthy is usually Home Assistant's
  add-on being down, but it looks the same when ser2net cannot start, read its
  config or open the radio, so check the connection first and then its logs. see
  [thread radio over the network](#thread-radio-over-the-network)
- `zigbee2mqtt` is defined here but not deployed. its stack was created while the
  Sonoff dongle was out, and a failed create takes the stack record with it, so
  nothing polls that branch until the stack is created again. **check the
  hardware is present before creating a stack that needs it**

## /docker-data

every stack's state lives under one directory, so one directory is what gets
backed up:

| path | owner | holds |
| --- | --- | --- |
| `/docker-data/zwavejs2mqtt/store` | `alex` | the Z-Wave network: settings, keys, node cache, logs |
| `/docker-data/ser2net/data` | `alex` | `ser2net.yaml` |
| `/docker-data/zigbee2mqtt/data` | `alex` | zigbee2mqtt config and database |

the directory names predate the apps' current names (`zwavejs2mqtt` is now
`zwave-js-ui`). renaming them means changing the stacks too, so they stayed.

## thread radio over the network

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

### is it working

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

## GPS time

a MediaTek GPS module on the serial port (gpsd identifies it as `MTK-3301`) with
its PPS output on GPIO 4. gpsd reads it, chrony uses it. the serial data gives
the time to the second, the PPS pulse marks exactly when each second starts.

### gpsd

`/etc/default/gpsd`:

```
START_DAEMON="true"
DEVICES="/dev/ttyAMA0 /dev/pps0"
GPSD_OPTIONS="-n"
USBAUTO="false"
```

- `-n` makes gpsd talk to the GPS straight away rather than waiting for a
  client, which chrony needs
- `USBAUTO="false"` stops gpsd grabbing the USB radios, which are serial devices
  too

gpsd starts from `gpsd.socket` (enabled), and chrony pulls `gpsd.service` in.

### chrony

what i added to the end of `/etc/chrony/chrony.conf`, the rest is Debian's
default:

```
# GPS refclocks
refclock SHM 0 refid NMEA precision 1e-1 offset 0.2 delay 0.2 noselect
refclock PPS /dev/pps0 refid PPS lock NMEA precision 1e-7 prefer

# serve time to the LAN
allow 192.168.0.0/16
allow 2001:db8:1000::/56
allow fe80::/10
```

- `NMEA` is gpsd's time from the serial data, via shared memory. `noselect`
  because it is only good to a fraction of a second and is not used on its own.
  `offset 0.2` corrects for the time message arriving a little after the second
  it describes, so it lines up with the pulse
- `PPS` is the pulse, `lock NMEA` pairs each pulse with the NMEA time to know
  which second it belongs to, `prefer` makes it the source when it is working
- the default pool servers stay in, so when there is no GPS fix chrony carries on
  from the internet

- `allow` turns chrony from a client into an NTP server for those ranges.
  without any `allow` line it serves nobody

`/etc/systemd/system/chrony.service.d/override.conf` starts chrony after gpsd:

```ini
[Unit]
After=gpsd.service
Wants=gpsd.service
```

clients use it as `ntp.yourdomain.com`, a DNS CNAME to the pi. check the CNAME
target carefully, a typo in the domain points your clocks at someone else's
domain, which fails quietly until somebody registers the name.

### checking it

```
chronyc sources         # #* PPS means the pulse is the source, #? means no usable samples
gpspipe -w | grep TPV   # "mode":3 is a 3D fix, 2 is 2D, 1 is no fix
sudo ppstest /dev/pps0  # prints a line per second when pulses arrive
```

most GPS modules only pulse once they have a fix, so no fix means no pulses, and
chrony shows both GPS sources as `#?` while it keeps time from the pool. a fix needs
sky view. mine had none until the antenna was fitted.

from any other machine, the pi should answer as **stratum 1** with reference
`PPS`. on mine it does, over IPv4 and IPv6, a few milliseconds from the LAN.

## PoE HAT OLED

the pi is powered over ethernet by a PoE HAT with a small OLED, which runs the
HAT maker's example Python script as a service. it talks to the display over
i2c, hence `dtparam=i2c_arm=on` and `i2c-dev` in `/etc/modules`.

`/etc/systemd/system/POE_OLED_Python_Service.service`:

```ini
[Unit]
Description=POE OLED Python Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/alex/PoE_HAT_B_code/PoE_HAT_B_code/python/examples/main.py
WorkingDirectory=/home/alex/PoE_HAT_B_code/PoE_HAT_B_code/python/examples
StandardOutput=journal
StandardError=journal
Restart=always

[Install]
WantedBy=multi-user.target
```

the unit runs as root, so the script and its directories must be writable by root
only. vendor zips often unpack world-writable, and a world-writable script run by
root lets any local user run anything as root:

```
sudo chown -R root:root /home/alex/PoE_HAT_B_code
sudo chmod -R go-w /home/alex/PoE_HAT_B_code
```

## backups

hourly to PBS, `/docker-data` plus reference copies of `/etc`, `/usr/local`,
`/root` and `/home`, see [raspberry pi to PBS](../backups/pi-host-backup.md).
