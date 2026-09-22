---
title: "GPS Time"
---

# gps time

a MediaTek GPS module on the serial port (gpsd identifies it as `MTK-3301`) with
its PPS output on GPIO 4. gpsd reads it, chrony uses it. the serial data gives
the time to the second, the PPS pulse marks exactly when each second starts.

## gpsd

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

## chrony

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

clients use it as `ntp.mydomain.com`, a DNS CNAME to the pi. check the CNAME
target carefully, a typo in the domain points your clocks at someone else's
domain, which fails quietly until somebody registers the name.

## checking it

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

