---
title: "ESP Border Router"
---

# ESP border router

an Espressif board is my second border router. this page covers its parts,
building and flashing it, getting it onto the network, its web UI and REST API,
and firmware updates.

| | |
| --- | --- |
| hardware | Espressif ESP Thread Border Router/Zigbee Gateway board: ESP32-S3 host, ESP32-H2 radio co-processor, UART between them |
| backbone | Ethernet, on Espressif's Sub-Ethernet daughter board (W5500, 10/100), built with `CONFIG_EXAMPLE_CONNECT_ETHERNET`. the main board alone is Wi-Fi only. i wanted this border router as reliable as i could make it, so no Wi-Fi |
| power | PoE, through an external splitter. Espressif lists 5 V over either USB-C port as the board's only power input, and neither board has PoE |
| firmware | [esp-thread-br](https://github.com/espressif/esp-thread-br) `basic_thread_border_router`, built from `main` at `46d36d3` on ESP-IDF v5.5.4 |

## what you need

| part | what for |
| --- | --- |
| [ESP Thread Border Router / Zigbee Gateway board](https://www.amazon.com/Thread-Border-Router-Zigbee-Gateway/dp/B0C89H9MJ8) | the border router: ESP32-S3 host, ESP32-H2 radio. `main`'s default partitions need its 8 MB of flash |
| [Sub-Ethernet daughter board](https://www.amazon.com/Thread-Border-Router-Gateway-Sub-Ethernet/dp/B0C89J43LN) | the wired backbone. it stacks on the main board's headers |
| [802.3af PoE splitter with 5 V out](https://www.amazon.com/ANVISION-Gigabit-Splitter-802-3af-Compliant/dp/B08J41JNF8) | one cable to the board: Ethernet for the daughter board, 5 V for the board |
| a barrel to USB-C lead | the splitter's DC output into a USB-C port |
| a USB-C **data** cable | flashing, from your computer. charge-only cables will not enumerate |
| [a printed case](https://www.printables.com/model/1194883-esp-thread-border-router-case-ethernet) | optional. fits the two boards stacked, with the Ethernet socket out the side |

the two USB-C ports are **USB1** (the H2) and **USB2** (the S3). both feed the
board through diodes, so power on one and your computer on the other at the same
time is fine. mine keeps power on USB1 and leaves USB2 for flashing.

## build and flash it

the board arrives blank: it does nothing until you flash Espressif's
`basic_thread_border_router` example onto the S3. the H2 gets its radio firmware
from the S3 on first boot, so you only flash one of them.

1. install ESP-IDF's prerequisites, from Espressif's
   [setup guide](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32s3/get-started/linux-macos-setup.html)
   for your OS. run their commands, not a summary of them:

    - **Linux**, Debian and Ubuntu:

        ```
        sudo apt-get install git wget flex bison gperf python3 python3-pip python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0
        ```

        also add yourself to the `dialout` group (`uucp` on some distributions),
        or flashing fails with a permission error on the port

    - **macOS**: `brew install cmake ninja dfu-util ccache`. ESP-IDF uses the
      system python3
    - **Windows**: the
      [ESP-IDF Windows installer](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32s3/get-started/windows-setup.html),
      which is the supported path rather than WSL. its **ESP-IDF PowerShell**
      shortcut sets the environment up for you, but only for the tree
      **the installer** manages. so either:

        - pick **v5.5.4** in the installer, use that shortcut, and skip the
          `esp-idf` clone in the next step, or
        - clone as below and activate that clone yourself, in PowerShell:
          `.\esp-idf\install.ps1 esp32s3,esp32h2` then `. .\esp-idf\export.ps1`

        get this wrong and `idf.py` runs against a different ESP-IDF from the one
        you built the radio firmware in

2. get both trees. on Windows that is `install.ps1` in PowerShell, or
   `install.bat` in the Command Prompt. every `idf.py` below runs in a shell where
   you have sourced the matching `export` script for **this** tree, unless you let
   the installer manage it

    ```
    git clone -b v5.5.4 --depth 1 --recursive https://github.com/espressif/esp-idf.git
    ./esp-idf/install.sh esp32s3,esp32h2
    git clone https://github.com/espressif/esp-thread-br.git
    git -C esp-thread-br checkout 46d36d3
    ```

3. put your settings in a second defaults file rather than editing anything.
   mine is `sdkconfig.esp-ot-br` in `esp-thread-br/examples/basic_thread_border_router`:

    ```
    CONFIG_EXAMPLE_CONNECT_ETHERNET=y
    # CONFIG_EXAMPLE_CONNECT_WIFI is not set
    CONFIG_OPENTHREAD_BR_AUTO_START=y
    CONFIG_OPENTHREAD_BR_START_WEB=y
    CONFIG_OPENTHREAD_COMMISSIONER=y
    CONFIG_OPENTHREAD_JOINER=y
    CONFIG_OPENTHREAD_RADIO_STATS_ENABLE=y
    CONFIG_OPENTHREAD_TIME_SYNC=y
    CONFIG_OPENTHREAD_PACKAGE_NAME="openthread-unit1"
    ```

    you do not need to set the radio link. the board's defaults already have it:

    ```
    CONFIG_PIN_TO_RCP_TX=17
    CONFIG_PIN_TO_RCP_RX=18
    CONFIG_PIN_TO_RCP_RESET=7
    CONFIG_PIN_TO_RCP_BOOT=8
    CONFIG_AUTO_UPDATE_RCP=y
    ```

    with `AUTO_UPDATE_RCP` the S3 flashes the H2 with the radio firmware it was
    built with, over the reset and boot pins

4. give the board a name of its own. Espressif's code sets the same name,
   `esp-ot-br`, on every board, so a second one answers to the same
   `esp-ot-br.local` as the first. one line in `main/esp_ot_br.c` names it after
   its own MAC instead, the way the firmware already names the network it forms:

    ```c
    uint8_t mac[6];
    char hostname[32];
    ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_BASE));
    snprintf(hostname, sizeof(hostname), "esp-ot-br-%02x%02x", mac[4], mac[5]);
    ESP_ERROR_CHECK(mdns_hostname_set(hostname));
    ```

    add `#include "esp_mac.h"` at the top, and replace the line that reads
    `mdns_hostname_set("esp-ot-br")`. this renames the web UI, the REST API and
    the name Home Assistant shows. it is a change to Espressif's code, so
    re-apply it at each firmware update

    mine came out as `esp-ot-br-33f0.local`, and every example on this page uses
    that name. yours ends in your own four characters, which the board prints on
    the console at boot and shows in the web UI. skip this step and it stays
    `esp-ot-br.local`

5. build the radio firmware first, because the border router build packs it into
   its `rcp_fw` partition. on Linux and macOS:

    ```
    cd "$IDF_PATH/examples/openthread/ot_rcp" &&
      idf.py set-target esp32h2 && idf.py build

    cd ~/esp-thread-br/examples/basic_thread_border_router &&
      export SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.esp-ot-br" &&
      idf.py set-target esp32s3 && idf.py build
    ```

    in the ESP-IDF PowerShell, `export` does not exist and `&&` only works in
    PowerShell 7, so the commands there are separate:

    ```
    cd "$env:IDF_PATH\examples\openthread\ot_rcp"
    idf.py set-target esp32h2
    idf.py build

    cd $HOME\esp-thread-br\examples\basic_thread_border_router
    $env:SDKCONFIG_DEFAULTS = "sdkconfig.defaults;sdkconfig.esp-ot-br"
    idf.py set-target esp32s3
    idf.py build
    ```

    - `IDF_PATH` is set by the `export` script, or by the installer's shortcut on
      Windows, and points at whichever ESP-IDF you activated. using it means these
      commands work whether that tree sits beside `esp-thread-br` or wherever the
      installer put it
    - the second `cd` is wherever you cloned `esp-thread-br`
    - the commands are chained because `idf.py set-target` clears the build
      directory: after a `cd` that failed, the next command wipes the radio
      firmware build. on Windows, check each command worked before the next

6. plug your computer into **USB2** and flash. the S3 appears as a USB serial
   device: `/dev/ttyACM0` on Linux, `/dev/cu.usbmodemXXXX` on macOS, `COM4` or
   similar on Windows. it needs no driver, because it is the chip's own USB

    ```
    idf.py -p <port> flash
    ```

7. first boot takes about 15 seconds: the S3 flashes the H2 with the radio
   firmware, restarts, brings up Ethernet, and serves its web UI at
   `http://esp-ot-br-33f0.local`. `idf.py -p <port> monitor` shows it, and
   restarts the board when it connects

the board does not join anything by itself. with no dataset stored it forms a
network of its own on a random channel and becomes its leader. that network is
named `ESP-BR-xxxx` after the board's MAC. this is expected, and the next
section moves the board onto yours.

## get it onto your network

Home Assistant can push your network onto the board, which is much better than
copying dataset TLVs around by hand. the panel only offers it for a border router
it *manages*, so add it to the integration first.

1. **Settings** > **Devices & services** > **Add integration** > **OpenThread
   Border Router**, URL `http://esp-ot-br-33f0.local`. the ESP is on port 80. a
   standard border router uses 8081
2. rename both entries, ⋮ > **Rename**. the one you add by URL is always called
   *Open Thread Border Router*, and the app's entry takes the app's name,
   *OpenThread Border Router*: the two differ by one space. mine say `(ESP32)` and `(add-on + ser2net)`. to
   tell them apart, use ⋮ > **Download diagnostics**: the URL is in the JSON
3. **Settings** > **Devices & services** > **Thread**. the board shows under its
   own `ESP-BR-xxxx` network. on **its row**, ⋮ > **Add to preferred network**
4. the dialog says *Home Assistant will join an existing Thread network. Any
   devices that are currently joined on this Home Assistant Thread network will
   need to be re-joined*. it reads backwards: it pushes **your** preferred dataset
   onto **the board**. the devices it means are the ones on the network the board
   is leaving, which is its own empty one. press **OK**
5. it attaches as a child and is a router a minute or two later

    ```
    curl -s http://esp-ot-br-33f0.local/node/state; echo
    ```

6. the empty `ESP-BR-xxxx` network is left behind in the panel. delete it with the
   bin icon on its card

<!-- -->

- **do not press Make preferred network** on the `ESP-BR-xxxx` card. that promotes
  the board's own network instead of moving the board
- adding the integration only reads: Home Assistant fetches the active dataset and
  stores it, and writes nothing to the board until you ask it to
- **Create network** on a border router factory resets it first. never use it on
  a working one
- entries are matched on the border agent ID. a firmware update keeps that ID, so
  the entry survives one, but an erase changes it and you delete and re-add
- if Home Assistant cannot resolve the name, use the address, and give it a DHCP
  reservation first

## web UI and REST API

- web UI: `http://esp-ot-br-33f0.local/`
- `http://esp-ot-br-33f0.local/.well-known/thread/esp-br-rest` lists the API
- the REST API has the same shape as OpenThread's own border router's:

    ```
    curl -s http://esp-ot-br-33f0.local/node/state; echo
    curl -s http://esp-ot-br-33f0.local/node
    curl -s http://esp-ot-br-33f0.local/diagnostics
    curl -s http://esp-ot-br-33f0.local/topology
    ```

    `/node/state` answers `"disabled"`, `"detached"`, `"child"`, `"router"` or
    `"leader"`. in `/node` the same thing is a number, 0 to 4 in that order

- the answers are not shaped alike: `/topology` and `/ipaddr` wrap theirs in a
  `result` field, while `/diagnostics` is a bare array and `/node` a bare object.
  so `jq` needs `.result[]` for the first two and `.[]` for `/diagnostics`
- a path it does not know returns HTTP 200 with a 404 error in the body, so read
  the body, not the status code
- the OpenThread console is on the S3's USB-C port, not on the network. its
  commands need an `ot` prefix (`ot state`). plain
  `idf.py -p /dev/cu.usbmodemXXXX monitor` restarts the S3 when it connects.
  `--no-reset` is meant to stop that. i have not tried it

**there is no authentication.** anyone on the LAN can read the dataset, network key
included, from `/node/dataset/active`, read the PSKc from the web UI's
`/get_properties`, stop Thread, or make it join or form another network. i accept
that on my LAN. if you do not, build with `CONFIG_OPENTHREAD_BR_START_WEB` off and
use the USB console.

![the ESP web UI scan: the Amazon network on channel 11, and two routers of the Home Assistant network on channel 15](../assets/img/esp-ot-br-scan.png)

## joining it by hand

[the panel](#get-it-onto-your-network) does this for you. by hand is for when it
cannot: no Home Assistant, or a border router it does not manage.

some things do not work, or not the way you would expect:

- **the menuconfig dataset** (**Component config** > **OpenThread** > **Thread
  Operational Dataset**) is ignored. with nothing stored the board forms its own
  `ESP-BR-xxxx` network instead
- **Join in the web UI** once started from a random new network and copied in only
  the channel, PAN ID and key, leaving the name, extended PAN ID and mesh-local
  prefix random. this build has the fix, but i have not used it
- **Form** in the web UI makes a new network

a board that attaches but stays a **child** has a dataset that differs from the
network's, usually in the mesh-local prefix. with the same active timestamp on
both, it never takes the network's copy, and pushing the dataset is what fixes it.

check what it has. to keep the key off the screen, `jq` picks out four fields:

```
curl -s http://esp-ot-br-33f0.local/node/dataset/active | jq '{NetworkName, Channel, MeshLocalPrefix, ActiveTimestamp}'
```

in Home Assistant's **Active dataset TLVs**, the mesh-local prefix is the 16 hex
characters after `0708` (type 7, length 8). if they differ, push the dataset.

going through the clipboard keeps the network key out of shell history and
files. steps 1, 2 and 4 differ per platform and i only run the macOS ones. the
installer's shortcut opens Windows PowerShell 5.1, where `curl` is an alias for
`Invoke-WebRequest` rather than curl itself and does not understand `-s`, `-o`,
`-w` or `-X`. call `curl.exe` for the reads, and use the `Invoke-RestMethod`
lines below for the writes. PowerShell 7 dropped that alias, so there `curl` is
the real thing.

1. stop Thread. it only takes a new active dataset while stopped. expect `200`

    ```
    curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H 'Content-Type: application/json' -d '"disable"' http://esp-ot-br-33f0.local/node/state
    ```

    the PowerShell version throws on anything but a 2xx rather than printing a
    code:

    ```
    Invoke-RestMethod -Method Put -ContentType 'application/json' -Body '"disable"' -Uri http://esp-ot-br-33f0.local/node/state
    ```

2. copy **Active dataset TLVs** from Home Assistant, then send it from the
   clipboard and overwrite the clipboard. expect `200`. macOS:

    ```
    pbpaste | tr -d '[:space:]' | curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H 'Content-Type: text/plain' --data-binary @- http://esp-ot-br-33f0.local/node/dataset/active
    pbcopy < /dev/null
    ```

    on Linux over ssh there is no desktop, so no clipboard. `read -rs` takes the
    paste without echoing it. `read` is a shell builtin, so the key stays out of
    the history, files and the process list:

    ```
    read -rs TLV
    printf '%s' "$TLV" | tr -d '[:space:]' | curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H 'Content-Type: text/plain' --data-binary @- http://esp-ot-br-33f0.local/node/dataset/active
    unset TLV
    ```

    paste at the blank line and press Enter. `-s` is bash and zsh. on a shell
    without it the paste is echoed, which is only a shoulder-surfing problem

    PowerShell has no `tr` or `pbcopy`. without `-Raw`, `Get-Clipboard` hands
    back one string per line, and the PUT then carries an array rather than the
    dataset. `Set-Clipboard` will not take an empty string, so the last line
    overwrites the clipboard with a space:

    ```
    $tlv = (Get-Clipboard -Raw) -replace '\s', ''
    Invoke-RestMethod -Method Put -ContentType 'text/plain' -Body $tlv -Uri http://esp-ot-br-33f0.local/node/dataset/active
    Set-Clipboard -Value ' '
    ```

    the values in the TLVs replace the stored ones

3. run the check above. the mesh-local prefix should now match
4. start Thread

    ```
    curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H 'Content-Type: application/json' -d '"enable"' http://esp-ot-br-33f0.local/node/state
    ```

    PowerShell:

    ```
    Invoke-RestMethod -Method Put -ContentType 'application/json' -Body '"enable"' -Uri http://esp-ot-br-33f0.local/node/state
    ```

5. after two or three minutes `/node/state` should say `"router"`. if it sits at
   `"detached"`, power cycle the board. it starts from the stored dataset

## firmware updates

an update is the same build as [above](#build-and-flash-it), with three
differences.

1. keep the old tree. clone the new ESP-IDF and esp-thread-br into new
   directories, so the build you are running now is still there
2. back up the flash before writing anything

    ```
    esptool.py --chip esp32s3 -p <port> read_flash 0 ALL esp-ot-br-backup.bin &&
      idf.py -p <port> flash
    ```

    - the `&&` stops the flash if the backup fails. in PowerShell run the two
      separately and check the backup exists first
    - the backup takes about 12 minutes and holds the network key, so keep it
      out of git. the way back is `esptool.py write_flash 0` with that backup
      file. i have not needed it

3. **never `idf.py erase-flash`.** a normal flash keeps the dataset, the border
   agent ID and the board's place in the network. an erase loses all three, and
   you start again at [get it onto your network](#get-it-onto-your-network)

then `/node/state` should say `"router"` within a couple of minutes and the
[dataset check](#joining-it-by-hand) should still match Home Assistant.

`/diagnostics` and `/topology` do not return `NetworkData`, `Connectivity`,
`MACCounters` or `ChannelPages`, so network data comes from the USB console, see
[what each border router publishes](checking-the-mesh.md#what-each-border-router-publishes).
