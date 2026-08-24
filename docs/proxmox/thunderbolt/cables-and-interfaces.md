---
title: "Thunderbolt Networking"
source_gist: https://gist.github.com/scyto/67fdc9a517faefa68f730f82d7fa3570
---

# Thunderbolt Networking

[this gist is part of this series](../index.md)

#### you wil need proxmox kernel 6.2.16-14-pve or higher.

## Load Kernel Modules
- add `thunderbolt` and `thunderbolt-net` kernel modules (this must be done all nodes - yes i know it can sometimes work withoutm but the thuderbolt-net one has interesting behaviou' so do as i say - add both ;-)
    1. `nano /etc/modules` add modules at bottom of file, one on each line	
    2. save using `x` then `y` then `enter`

## Prepare /etc/network/interfaces
doing this means we don't have to give each thunderbolt a manual IPv6 addrees and that these addresses stay constant no matter what
Add the following to each node using `nano /etc/network/interfaces`

If you see any sections called thunderbolt0 or thunderbol1 delete them at this point.

### Create entries to prepopulate gui with reminder
Doing this means we don't have to give each thunderbolt a manual IPv6 or IPv4 addrees and that these addresses stay constant no matter what.

Add the following to each node using `nano /etc/network/interfaces` this to remind you not to edit en05 and en06 in the GUI

This fragment should go between the existing `auto lo` section and adapater sections.

```
iface en05 inet manual
#do not edit it GUI

iface en06 inet manual
#do not edit in GUI
```

If you see any thunderbol sections delete them from the file before you save it.

**DO NOT DELETE* the `source /etc/network/interfaces.d/*` this will always exist on the latest versions and should be the last or next to last line in /interfaces file

## Rename Thunderbolt Connections
This is needed as proxmox doesn't recognize the thunderbolt interface name.  There are various methods to do this. This method was selected after trial and error because:
- the thunderboltX naming is not fixed to a port (it seems to be based on sequence you plug the cables in)
- the MAC address of the interfaces changes with most cable insertion and removale events


1. use `udevadm monitor` command to find your device IDs when you insert and remove each TB4 cable. Yes you can use other ways to do this, i recommend this one as it is great way to understand what udev does - the command proved more useful to me than `the syslog` or `lspci command` for troublehsooting thunderbolt issues and behavious.  In my case my two pci paths are `0000:00:0d.2`and `0000:00:0d.3` if you bought the same hardware this will be the same on all 3 units. Don't assume your PCI device paths will be the same as mine.

2. create a link file using `nano /etc/systemd/network/00-thunderbolt0.link` and enter the following content:

```
[Match]
Path=pci-0000:00:0d.2
Driver=thunderbolt-net
[Link]
MACAddressPolicy=none
Name=en05
```
3. create a second link file using `nano /etc/systemd/network/00-thunderbolt1.link` and enter the following content:
```
[Match]
Path=pci-0000:00:0d.3
Driver=thunderbolt-net
[Link]
MACAddressPolicy=none
Name=en06
```

## Set Interfaces to UP on reboots and cable insertions
This section en sure that the interfaces will be brought up at boot or cable insertion with whatever settings are in /etc/network/interfaces  - this shouldn't need to be done, it seems like a bug in the way thunderbolt networking is handled (i assume this is debian wide but haven't checked).

Huge thanks to @corvy for figuring out a script that should make this much much more reliable for most

1. create a udev rule to detect for cable insertion using `nano /etc/udev/rules.d/10-tb-en.rules` with the following content:
```
ACTION=="move", SUBSYSTEM=="net", KERNEL=="en05", RUN+="/usr/local/bin/pve-en05.sh"
ACTION=="move", SUBSYSTEM=="net", KERNEL=="en06", RUN+="/usr/local/bin/pve-en06.sh"
```
2. save the file

3. create the first script referenced above using `nano /usr/local/bin/pve-en05.sh` and with the follwing content:
```
#!/bin/bash

LOGFILE="/tmp/udev-debug.log"
VERBOSE="" # Set this to "-v" for verbose logging
IF="en05"

echo "$(date): pve-$IF.sh triggered by udev" >> "$LOGFILE"

# If multiple interfaces go up at the same time, 
# retry 10 times and break the retry when successful
for i in {1..10}; do
    echo "$(date): Attempt $i to bring up $IF" >> "$LOGFILE"
    /usr/sbin/ifup $VERBOSE $IF >> "$LOGFILE" 2>&1 && {
        echo "$(date): Successfully brought up $IF on attempt $i" >> "$LOGFILE"
        break
    }
  
    echo "$(date): Attempt $i failed, retrying in 3 seconds..." >> "$LOGFILE"
    sleep 3
done
```
save the file and then

3. create the second script referenced above using `nano /usr/local/bin/pve-en06.sh` and with the follwing content:
```
#!/bin/bash

LOGFILE="/tmp/udev-debug.log"
VERBOSE="" # Set this to "-v" for verbose logging
IF="en06"

echo "$(date): pve-$IF.sh triggered by udev" >> "$LOGFILE"

# If multiple interfaces go up at the same time, 
# retry 10 times and break the retry when successful
for i in {1..10}; do
    echo "$(date): Attempt $i to bring up $IF" >> "$LOGFILE"
    /usr/sbin/ifup $VERBOSE $IF >> "$LOGFILE" 2>&1 && {
        echo "$(date): Successfully brought up $IF on attempt $i" >> "$LOGFILE"
        break
    }
  
    echo "$(date): Attempt $i failed, retrying in 3 seconds..." >> "$LOGFILE"
    sleep 3
done
```
and save the file

4. make both scripts executable with `chmod +x /usr/local/bin/*.sh`
5. run `update-initramfs -u -k all` to propogate the new link files into initramfs
6. Reboot (restarting networking, init 1 and init 3 are not good enough, so reboot)


## Enabling IP Connectivity
[proceed to the next gist](openfabric-mesh-legacy.md)

# Slow Thunderbolt Performance? Too Many Retries? No traffic? Try this!

## verify neighbors can see each other (connectivity troubleshooting)
##3 Install LLDP - this is great to see what nodes can see which.
-  install lldpctl with `apt install lldpd` on all 3 nodes
-  execute `lldpctl` you should info 

## make sure iommu is enabled (speed troubleshooting)
if you are having speed issues make sure the following is set on the kernel command line in `/etc/default/grub` file
`intel_iommu=on iommu=pt`
one set be sure to run `update-grub` and reboot

everyones grub command line is different this is mine because i also have i915 virtualization, if you get this wrong you can break your machine, if you are not doing that you don't need the i915 entries you see below

`GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"` (note if you have more things in your cmd line DO NOT REMOVE them, just add the two intel ones, doesnt matter where.


## Pinning the Thunderbolt Driver (speed and retries troubleshooting)

### identify you P and E cores by running the following

```
cat /sys/devices/cpu_core/cpus && cat /sys/devices/cpu_atom/cpus
```
you should get two lines on an intel system with P and E cores.
first line should be your P cores
second line should be your E cores

for example on mine:
```
root@pve1:/etc/pve# cat /sys/devices/cpu_core/cpus && cat /sys/devices/cpu_atom/cpus
0-7
8-15
```

### create a script to apply affinity settings everytime a thunderbolt interface comes up

1. make a file at `/etc/network/if-up.d/thunderbolt-affinity`
2. add the following to it - make sure to replace `echo X-Y` with whatever the report told you were your performance cores - e.g. `echo 0-7` 

```
#!/bin/bash

# Check if the interface is either en05 or en06
if [ "$IFACE" = "en05" ] || [ "$IFACE" = "en06" ]; then
# Set Thunderbot affinity to Pcores
    grep thunderbolt /proc/interrupts | cut -d ":" -f1 | xargs -I {} sh -c 'echo X-Y | tee "/proc/irq/{}/smp_affinity_list"'
fi
```
3. save the file - done

## Extra Debugging for Thunderbolt

### dynamic kernel tracing - adds more info to dmesg, doesn't overhwelm dmesg
I have only tried this on 6.8 kernels, so YMMV
If you want more TB messages in dmesg to see why connection might be failing here is how to turn on dynamic tracing

For bootime you will need to add it to the kernel command line by adding `thunderbolt.dyndbg=+p` to your /etc/default/grub file, running `update-grub` and rebooting.  

To expand the example above"

    `GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt thunderbolt.dyndbg=+p"`  

Don't forget to run `update-grub` after saving the change to the grub file.

For runtime debug you can run the following command (it will revert on next boot) so this cant be used to cpature what happens at boot time.

    `echo -n 'module thunderbolt =p' > /sys/kernel/debug/dynamic_debug/control`

### install tbtools
these tools can be used to inspect your thundebolt system, note they rely on rust to be installedm you must use the rustup script below and not intsall rust by package manager at this time (9/15/24)

```
apt install pkg-config libudev-dev git curl
curl https://sh.rustup.rs -sSf | sh
git clone https://github.com/intel/tbtools
restart you ssh session
cd tbtools
cargo install --path .
```
