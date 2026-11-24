# Xunzel IXS ON Series — LCD Setting menu (manual pages 28-43)

Transcribed from the paper manual that ships with the Xunzel IXS-ON 7200 (PACK ZERO+ AX 490 L
kit), chapter 07 "LCD SETTING", pages 28-43. This is a reference for the **front-panel menu
only** — nothing on this page is sent or received over RS-232. See
[PROTOCOL.md](PROTOCOL.md) for the serial protocol, and section 7 of that file for the two
entries below (Program 37 and Program 93) that must never be confirmed on the panel because
they would erase the totals the RS-232 energy commands read back.

**How to enter the menu:** press and hold the Enter/confirm button (`↵`) for 3 seconds to enter
Setup Mode. Press `▲` or `▼` to pick a program number, `↵` to confirm a selection, or the
`USB/⏻` button to exit.

Each program below shows: the program number, what it configures, the selectable options, the
program's own LCD code, and each option's LCD code. "(default)" marks the factory default.

## General settings (00-05)

| Program | Description | Option | LCD shows |
|---|---|---|---|
| 00 | Exit setting mode | Escape | `00` → `ESC` |
| 01 | Output source priority: which source feeds the loads | Utility first (default) — utility feeds the loads; solar/battery only take over when utility is unavailable | `01` → `USb` |
| 01 | | Solar first — solar feeds the loads first; utility helps only if solar can't cover everything, at the same time as solar | `01` → `SUb` |
| 01 | | SBU priority — solar feeds the loads first; if insufficient, battery helps at the same time; utility only steps in once battery drops to the low-level warning voltage or the point set in Program 12 | `01` → `SbU` |
| 02 | Maximum charging current (utility charging current + solar charging current) | 10 A / 20 A / 30 A / 40 A / 50 A / 60 A (default) / 70 A (3kW/5kW only) / 80 A (3kW/5kW only) | `02` → `10`/`20`/`30`/`40`/`50`/`60`/`70`/`80` |
| 03 | AC input voltage range | Appliances (default) — accepts 90-280 VAC | `03` → `APL` |
| 03 | | UPS — accepts 170-280 VAC | `03` → `UPS` |
| 05 | Battery type | AGM (default) | `05` → `AGn` |
| 05 | | Flooded | `05` → `FLd` |
| 05 | | User-Defined — lets you set charge voltage and low-DC cut-off yourself via Programs 26, 27, 29 | `05` → `USE` |
| 05 | | Pylontech battery — Programs 02, 26, 27 and 29 set automatically, no further setting needed | `05` → `PYL` |
| 05 | | WECO battery (48 V model only) — Programs 02, 12, 26, 27 and 29 auto-configured per the battery supplier's recommendation, no further adjustment | `05` → `uEC` |
| 05 | | Soltaro battery (48 V model only) — Programs 02, 26, 27 and 29 set automatically | `05` → `SOL` |
| 05 | | **LIb-protocol compatible battery** — select "LIb" if using a lithium battery compatible with the LIb protocol; Programs 02, 26, 27 and 29 are then set automatically, no further setting needed | `05` → `LIb` |
| 05 | | 3rd-party Lithium battery — Programs 02, 26, 27 and 29 set automatically; contact the battery supplier for the installation procedure | `05` → `LIC` |

This kit's inverter has Program 05 set to **LIb** on the front panel, and the live RS-232
`QPIRI`/`QDI` read reports battery-type code **8** (a value the 2014 generic protocol document
doesn't define). The code above (`05`) printed under every option is just the program number
repeated — the same way every other program repeats its own number across its options — not a
per-option index, so we can't read an exact numeric code for LIb off this page; `8` is simply
whatever the firmware uses internally for the option the panel displays as `LIb`.

## Restart, frequency and output (06-11)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 06 | Auto restart when overload occurs | Restart disable (default) / Restart enable | `06` → `Ltd` / `LtE` |
| 07 | Auto restart when over-temperature occurs | Restart disable (default) / Restart enable | `07` → `ttd` / `ttE` |
| 09 | Output frequency | 50 Hz (default) / 60 Hz | `09` → `50` / `60` |
| 10 | Output voltage | 220 V / 230 V (default) / 240 V | `10` → `220` / `230` / `240` |
| 11 | Maximum utility charging current. If Program 02's value is lower than Program 11's, the inverter uses Program 02's value for the utility charger instead | 2 A / 10 A / 20 A / 30 A (default) / 40 A / 50 A (3kW/5kW only) / 60 A (3kW/5kW only) | `11` → `UtI` + current value |

## SBU timing and charger source (12-16)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 12 | Voltage point to go back to the utility source, when "SBU" is selected in Program 01 | Standard model: 22.0 to 25.5 V in 0.5 V steps, 23.0 V default; 5kW model: 44 to 51 V in 1 V steps, 46 V default | `12` → voltage value, e.g. `230` (standard default) or `460` (5kW default) |
| 13 | Voltage point to go back to battery mode, when "SBU" is selected in Program 01 | 1.5kW/3kW model: "Battery fully charged" or 24 V (default `24.0`); 5kW model: 24.5 to 50 V in 0.5 V steps, "Battery fully charged" (`FUL`), 48/49/50 V, default 27 V | `13` → `FUL` or voltage value |
| 16 | Charger source priority (only applies while the unit is in Line, Standby or Fault mode) | Solar first — solar charges first; utility only if solar is unavailable | `16` → `CSO` |
| 16 | | Solar and Utility (default) — both charge the battery at the same time | `16` → `SnU` |
| 16 | | Only Solar — only solar can ever charge the battery, even if utility is available; in Battery mode only solar can charge regardless of this setting | `16` → `OSO` |

## Alarms, display, backlight, bypass (18-23)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 18 | Alarm control | Alarm on (default) / Alarm off | `18` → `bON` / `bOF` |
| 19 | Auto return to default display screen | Return to default screen after 1 minute of no button press (default) | `19` → `ESP` |
| 19 | | Stay at the latest screen the user switched to | `19` → `tEP` |
| 20 | Backlight control | Backlight on (default) / off | `20` → `LON` / `LOF` |
| 22 | Beeps while primary source is interrupted | Alarm on (default) / off | `22` → `AON` / `AOF` |
| 23 | Overload bypass — transfer to line mode if overload occurs in battery mode | Bypass disable (default) / Bypass enable | `23` → `byd` / `byE` |

## Fault log and charging voltages (25-29)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 25 | Record fault code | Record enable (default) / Record disable | `25` → `FEN` / `FdS` |
| 26 | Bulk charging voltage (C.V. voltage) | 1.5kW/3kW default 28.2 V (shown `CU 282`); 5kW default 56.4 V (shown `CU 564`). If "User-Defined" (Program 05), range is 25.0-31.5 V (1.5kW/3kW) or 48.0-61.0 V (5kW), 0.1 V steps | `26` → `CU` + voltage |
| 27 | Floating charging voltage | 1.5kW/3kW default 27.0 V (`FLU 270`); 5kW default 54.0 V (`FLU 540`). Same user-defined range rule as Program 26 | `27` → `FLU` + voltage |
| 29 | Low DC cut-off voltage — behavior: if battery is the only source, the inverter shuts down; if PV + battery are available, it charges without AC output; if PV + battery + utility are all available, it switches to line mode and supplies output | 1.5kW/3kW default 21.0 V (`COU 210`); 5kW default 42.0 V (`COU 420`). If user-defined, range is 21.0-24.0 V (1.5kW/3kW) or 42.0-48.0 V (5kW), 0.1 V steps; fixed regardless of load percentage | `29` → `COU` + voltage |

## Battery equalization (30-36)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 30 | Battery equalization (only settable if "Flooded" or "User-Defined" is selected in Program 05) | Battery equalization / Battery equalization disable (default) | `30` → `EEN` / `EdS` |
| 31 | Battery equalization voltage | 1.5kW/3kW default 29.2 V (`EU 292`); 5kW default 58.4 V (`EU 584`); range 25.0-31.5 V / 48.0-61.0 V, 0.1 V steps | `31` → `EU` + voltage |
| 33 | Battery equalized time | 60 min default (range 5-900 min, 5 min steps) | `33` → `60` |
| 34 | Battery equalized timeout | 120 min default (range 5-900 min, 5 min steps) | `34` → `120` |
| 35 | Equalization interval | 30 days default (range 0-90 days, 1 day steps) | `35` → `30d` |
| 36 | Equalization activated immediately (only settable if Program 30 is enabled) | Enable — starts equalization now, main screen shows `EQ` | `36` → `AEN` |
| 36 | | Disable (default) — cancels until the next scheduled time from Program 35; `EQ` stops showing | `36` → `AdS` |

## ⚠ Program 37 — destructive, never confirm

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 37 | **Reset all stored data for PV generated power and output load energy** | Not reset (default) | `37` → `nrt` |
| 37 | | **Reset** — wipes the PV/load energy totals the RS-232 `QET`/`QLT`/`QED`/`QEM`/`QEY`/`QLD`/`QLM`/`QLY` commands read | `37` → `rSt` |

## 7.2 kW model only (41)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 41 | Maximum discharging current (7.2 kW model only). If discharge current exceeds this, the battery stops discharging; the inverter runs on bypass if utility is available, or shuts down output for 5 minutes if not | Disable (default) — discharge protection off; or 30-150 A in 10 A steps | `41` → `dd5` (disable) or current value |

## RGB LED (51-55)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 51 | On/off control for RGB LED (must be enabled to activate RGB LED lighting) | Enabled (default) / Disable | `51` → `LEN` / `LdS` |
| 52 | Brightness of RGB LED | Low / Normal (default) / High | `52` → `LO` / `nOr` / `HI` |
| 53 | Lighting speed of RGB LED | Low / Normal (default) / High | `53` → `LO` / `nOr` / `HI` |
| 54 | RGB LED effects | Scrolling / Breathing / Solid on (default) | `54` → `5Cr` / `brE` / `5OL` |
| 55 | Color combination of RGB LED (shows energy source + battery charge/discharge status) | C01 (default): Violet-White-Sky blue, Pink-Honey | `55` → `C01` |
| 55 | | C02: White-Yellow-Green, Royal blue-Lime yellow | `55` → `C02` |

## ⚠ Program 93 — destructive, never confirm

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 93 | **Erase all data log** | Not reset (default) | `93` → `nrt` |
| 93 | | **Reset** — erases the entire data log | `93` → `rSt` |

## Data log interval and clock (94-99)

| Program | Description | Options | LCD shows |
|---|---|---|---|
| 94 | Data log recorded interval. Maximum log size is 1440 entries; once exceeded, it overwrites the oldest log | 3 / 5 / 10 (default) / 20 / 30 / 60 minutes | `94` → `3`/`5`/`10`/`20`/`30`/`60` |
| 95 | Time setting — minute | 0-59 | `95` → `nin` |
| 96 | Time setting — hour | 0-23 | `96` → `HOU` |
| 97 | Time setting — day | 1-31 | `97` → `dAY` |
| 98 | Time setting — month | 1-12 | `98` → `nOn` |
| 99 | Time setting — year | 17-99 (2017-2099) | `99` → `YEA` |

## Functional Setting (USB OTG and timers)

Three function keys on the panel give access to special functions beyond the numbered
programs: USB OTG functions, a timer for output source priority, and a timer for charger
source priority.

### 1. USB Function Setting

Insert an OTG USB disk, then press and hold the `USB/⏻` button for 3 seconds to enter USB
Setup Mode. This covers inverter firmware upgrade, data log export, and re-writing internal
parameters from a USB disk.

| Function | What it does | LCD shows |
|---|---|---|
| Upgrade firmware | Upgrades inverter firmware from the USB disk (check with dealer/installer for details) | `UPG` |
| Re-write internal parameters | Overwrites all parameter settings from a text file on the USB disk, or duplicates inverter settings | — |
| **Export data log** | Exports the data log from the inverter to the USB disk — a fully local way to get the full history off the inverter without polling RS-232 energy commands at all. Press the export button, confirm "Yes" when prompted (`tdY`); LED 1 flashes once per second during export; all LEDs light when done | `LOG`, confirm screen `tdY`, then `YES`/`nO` |

USB error codes: `U01` no USB disk detected; `U02` USB disk is write-protected; `U03` the file
on the USB disk has the wrong format. Error codes display for 3 seconds then the screen
returns to normal.

### 2. Timer Setting for Output Source Priority

Press and hold the relevant function button for 3 seconds to enter Timer Setup Mode for output
source priority, then set a start and end hour (00-23, 1-hour increments) for each priority
mode: Utility First (`USb`), Solar First (`SUb`), or SBU Priority (`SbU`).

### 3. Timer Setting for the Charger Source Priority

Same idea, for charger source priority per day: Solar First (`CSO`), Solar & Utility (`SnU`),
or Solar Only (`OSO`), each with a start/end hour.

## Display Setting

Pressing `▲`/`▼` on the main screen cycles through the available display screens. The default
screen shows input voltage and output voltage (e.g. `230`/`230`) together with the source/flow
icons (grid, MPPT, DC/DC, charging, DC/AC, battery, load). Other screens include the
`dAY`/`MON`/`YEA`/`tOL` PV-and-load-energy screens referenced in
[PROTOCOL.md section 6.8](PROTOCOL.md#68-energy-totals-qet-qlt-qed-qem-qey-qld-qlm-qly-verified),
and the firmware screens (`U1`, `U2`, `U3`).

---

*Transcribed by hand from photos of the printed manual for this project's own reference. Not a
substitute for the official Xunzel documentation — check xunzel.com or your dealer for the
authoritative version, and always read the full warning text in the manual itself before
changing any setting.*
