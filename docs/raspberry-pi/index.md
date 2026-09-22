---
title: "Raspberry Pi: pi-zwave01"
---

# raspberry pi: pi-zwave01

a Raspberry Pi 4 Model B that holds the USB radios for home automation, keeps
time from a GPS and serves it to the LAN, and shows its status on a small OLED. it is a standalone docker
host, not part of the swarm, and its stacks deploy from
[git](../docker/gitops-with-portainer.md) like everything else.

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
dns-search=mydomain.com;

[ipv6]
method=manual
address1=2001:db8:1000:1::96/64
gateway=2001:db8:1000:1::1
dns=2001:db8:1000:1::35;2001:db8:1000:1::36;
dns-search=mydomain.com;
```

the DNS servers are my two internal DNS servers, not the AdGuards.

## on these pages

<!-- this page used to hold all four. the empty spans keep its old section
anchors working, so a deep link lands on the link to where that section went -->

- <span id="docker"></span><span id="portainer-agent"></span><span id="radios-and-stacks"></span><span id="stacks-deployed-from-git"></span><span id="docker-data"></span>[docker and stacks](stacks.md) - docker, the portainer agent, the radios, and each container
- <span id="thread-radio-over-the-network"></span><span id="is-it-working"></span>[thread radio](thread-radio.md) - the SkyConnect shared over the network with ser2net
- <span id="gps-time"></span><span id="gpsd"></span><span id="chrony"></span><span id="checking-it"></span>[gps time](gps-time.md) - gpsd and chrony, serving stratum 1 time to the lan
- <span id="poe-hat-oled"></span>[poe hat oled](poe-oled.md) - the status display

## backups

hourly to PBS, `/docker-data` plus reference copies of `/etc`, `/usr/local`,
`/root` and `/home`, see [raspberry pi to PBS](../backups/pi-host-backup.md).
