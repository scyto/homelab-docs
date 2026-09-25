---
title: "PoE HAT OLED"
---

# poe hat oled

the pi is powered over ethernet by a PoE HAT with a small OLED. the HAT maker's
example Python script runs as a service and drives the display. it talks to the
display over i2c, hence `dtparam=i2c_arm=on` and `i2c-dev` in `/etc/modules`.

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

