---
title: "Fan Tuning"
---

# fan tuning

how i got truenas1 quiet enough to leave its closet door open, and how claude
tested it. the closet opens onto the home theatre, and it is not climate
controlled.

## where it started

the board's BMC ran every fan from `FSC_INDEX`, one index it computes for the
whole box, through one curve. so every fan answered every heat source. the CPU
fan ran near 6000 RPM at idle, and nothing sped up for the GPU in particular.

## where it ended

each fan follows the sensor that matches what it cools, through its own curve:

| header | fan | follows | idle before | idle now |
| --- | --- | --- | --- | --- |
| FAN1 | CPU cooler | `TEMP_CPU`, table 5 | 5800-6400 RPM | 2800 RPM |
| FAN2, FAN3 | drive wall | `TEMP_OUTLET2`, table 6 | 1200-1400 RPM | 1000 RPM |
| FAN4 | 60 mm fan over the PCIe slots | nothing, fixed at 100% | 3000-3200 RPM | 3200 RPM |
| FAN5 | rear | `TEMP_OUTLET2`, table 6 | 1000 RPM | 800 RPM |
| FAN6 | the M.2 card's own fan | `TEMP_OUTLET2`, table 7 | 2200-2400 RPM | 2400 RPM |

- air runs front to back. the drive wall pulls it over the drives and pushes
  it across the whole board side, past the CPU cooler, the memory, the GPU and
  the PCIe cards, and the rear fan takes it out. so the drive wall is the main
  airflow for everything on the board, not just the drives
- the board sits turned in the case, a Sliger CX4712, so its headers run FAN6
  to FAN1 from left to right
- the slot fan stays at full speed. NVMe drives on PCIe adapters cook without
  airflow, and the boot drives' controllers sit near 80 °C even with it

the BMC's temperature sensors, with the closet at about 29 °C:

| sensor | idle | GPU at its 350 W cap | fans on it |
| --- | --- | --- | --- |
| `TEMP_CPU` | 58-60 °C | 62-64 °C | FAN1 |
| `TEMP_OUTLET2` | 38-39 °C | 49-50 °C | FAN2, FAN3, FAN5, FAN6 |
| `TEMP_OUTLET1` | 48-49 °C | 48-49 °C | nothing |
| `FSC_INDEX` | 63-65 °C | 67-69 °C | the factory profile |
| `TEMP_MB2` | 36-37 °C | 49-50 °C | nothing |
| `TEMP_MB1` | 34 °C | 36 °C | nothing |
| `TEMP_LAN` | 64-66 °C | 64-67 °C | nothing |
| `TEMP_M.2_1`, `TEMP_M.2_2` | 46-48 °C | 54-56 °C | nothing |
| `TEMP_DDR5_*`, 8 DIMMs | 40-51 °C | 43-50 °C | nothing |

- `TEMP_OUTLET2` is the one that moves with the GPU, so the case fans and the
  M.2 card's fan follow it. `TEMP_OUTLET1` hardly moves whatever the load
- the BMC sees none of the add-in NVMe drives, the hard drives, the GPU or the
  network card. glances shows those, see [glances](../monitoring/glances.md)

the curves, as `°C duty%`:

| table | for | steps | hysteresis |
| --- | --- | --- | --- |
| 5 | CPU | 25 20, 66 25, 70 30, 74 40, 78 55, 82 70, 85 85, 88 100 | 5 °C |
| 6 | case fans | 25 35, 42 40, 46 50, 50 65, 53 80, 56 100 | 3 °C |
| 7 | M.2 card | 25 50, 42 60, 45 70, 48 85, 51 100 | 3 °C |

- each curve is a customized open-loop table, tied to its sensor and fans by a
  customized assignment, and each of those fans is set to customized. a fan can
  be in only one assignment, so take it out of the BMC's own first
- the CPU curve first rises at 66 °C, above where the CPU sits at idle and at
  half load, with 5 °C of hysteresis and a gradual ramp up, so the fan holds a
  speed rather than hunting between two
- at idle the case fans run at 35% and the M.2 card's fan at 50%, which i
  cannot hear. they speed up only when the GPU heats the case
- each table starts at 25 °C, below any reading the box gives, so nothing rests
  on what the BMC does below a table's first step
- redfish reports the fans but cannot set them. the BMC's web pages, and the
  API behind them, can
- a BMC reset or firmware update can bring the factory profile back, so the
  settings live in a file in my repo, with a script that checks the BMC against
  it and restores it. [gatus](../monitoring/gatus.md) watches the slot fan and
  the card's fan over redfish

## what it does under load

| load | result |
| --- | --- |
| a sustained write to `fast` | the Seagates level off at 60 °C; they are rated to 70 °C |
| a sustained mixed load on `rust` | the IronWolfs rise 1 to 2 °C |
| half the CPU's threads busy | the CPU holds 61 to 65 °C |
| the GPU at its 350 W cap | the GPU levels off at 81 °C, and the closet rises 2 °C |
| a sustained write to `fast` with the GPU busy | the Seagates pass 70 °C in about 7 minutes, even with the card's fan at full speed, because the GPU heats the air the card draws |

- nothing here loads `fast` that hard. the heaviest jobs, PBS's verifies and
  the offsite copy, read `rust`

## how claude tested it

the approach, not the scripts:

- before any change it saved the BMC's fan settings. a guard put them back the
  moment anything reached its limit
- a logger recorded every component once a minute: the fans and the BMC's
  sensors over redfish with a read-only account, every drive and card from
  glances, the GPU from `nvidia-smi`, and the closet from the UPS card's
  environment sensor
- each limit sat at or below the part's rating: 70 °C for the Seagates, 45 °C for the
  hard drives, 85 °C for the CPU and the GPU, 35 °C for the closet, and any fan
  under 300 RPM
- it changed the fans through the BMC's web API and read every change back. for
  the M.2 card's fan i stood at the server and listened at each step
- it loaded the box one source at a time, 12 minutes each with a cool-down
  between: a write to each pool on a throwaway dataset, half the CPU's threads,
  and the local sysadmin model writing runbooks on the GPU. then all of them at
  once. a watchdog stopped every load at the first limit, which is how the last
  row above ends
- the first pass showed the CPU fan hunting between two speeds and the case
  fans deaf to the GPU, so it changed the curves and ran the GPU and combined
  loads again
