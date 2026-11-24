# Xunzel IXS-ON 7200: read-only RS-232 monitoring

Read live values, settings and warnings from a **Xunzel IXS-ON 7200 W** solar inverter over its RS-232 port, using one small Python script with a menu. No packages to install.

It was built and tested on the **Xunzel PACK ZERO+ AX 490 L** solar kit (bought at Leroy Merlin in Portugal), and it only ever **reads**.

![Xunzel PACK ZERO+ AX 490 L wiring leaflet](docs/images/xunzel-pack-zero-plus-wiring-diagram.jpg)

*The wiring leaflet that comes with the kit (our photo, straightened and cleaned up). Leaflet artwork © Xunzel, shown only to identify the kit.*

---

## Read-only by design (and why)

> **This project never changes anything in the inverter. It only sends read commands.**

Why we are strict about it:

- **The kit is plug and play.** The PACK ZERO+ is sold as a matched set: lithium batteries, inverter, solar panels and PV protection. Xunzel pre-configured the inverter for it. Nothing needs to be set up.
- **The settings are not ours to touch.** The inverter's battery voltages, charge limits and battery type were chosen for the batteries in the kit. They differ from generic factory defaults (see [what we found](#what-we-found-on-this-inverter)). A wrong value can hurt the batteries.
- **Warranty.** Changing settings, or resetting the inverter, could make a warranty claim harder. We do not know exactly what Xunzel's warranty allows over RS-232, and we do not want to find out the hard way. So the rule is simple: look, never touch. Monitoring software normally works the same way, with read queries.
- **If you want to change a setting,** do it on the inverter itself, following Xunzel's instructions.

The rule is enforced in code, not just by good intentions: see [How read-only is enforced](#how-read-only-is-enforced).

**Not affiliated with Xunzel.** Names and logos belong to their owners. This is an independent hobby project. It is provided as is, under the MIT licence, with no warranty. You are responsible for your own equipment and for checking your own warranty terms.

---

## Why not the cloud app? (privacy)

Xunzel points buyers to the WatchPower / SolarPower phone apps (iOS and Android). Those apps work through a Wi-Fi module that sends the inverter's data to a **cloud server**. The platform maker's own description of its Wi-Fi module lists "cloud storage for history data and event log" and "remote monitoring and control of multiple inverters via mobile APP".

**That is not for us, and you may want to think about it too.**

- **Your electricity use is a diary of your life.** A record of when power is used, minute by minute, shows when you are home, when you sleep, when you are away on holiday, and more. That data should not be stored on someone else's server, or even pushed to one.
- **You cannot see where it goes.** Once the module is online, data can leave your house without you noticing. Who runs the server, where it is, and who can read the data is not something we could find out.
- **Remote control is the same door.** An app that can change settings from anywhere is exactly what we do not want near a battery system. This tool only reads.
- **A cable cannot leak.** A logger on the RS-232 port, on a network that has no route to the internet, has nothing to send anywhere.
- **Good to know: there is no local web page.** We asked Xunzel support how to reach the inverter's internal web page. Their friendly, quick answer (June 2026): "This inverter does not have an internal web interface." The inverter's Wi-Fi module gives you an address on its own network, but no page to open. So if you want local-only monitoring, the serial port is the way, and that is what this project is for.

To be fair: we have **not** captured the Wi-Fi module's network traffic, so we cannot say exactly what it sends. We only know what the manufacturer's documentation says it does. If you can measure it, please tell us.

On our kit the Wi-Fi module has never been connected to a home network, so we have not seen it send anything. The concern is about what it would do if it were. We also looked for a way to switch the module's radio off for a radio-free house. We found no setting in the manual or on the inverter's menu, and without an internal web page there is nowhere else to look. If you know a way, please tell us.

We have nothing against Xunzel. The kit works well and their support answered our question helpfully. This project exists to help other owners who want the same local, private setup.

---

## What you need

- A computer with **Python 3** (macOS or Linux; no extra packages).
- A **USB-to-RS-232 adapter** with a DB9 plug (we used one with an FTDI FT232R chip, which macOS recognises without a driver).
- A cable from the inverter's **RJ45 RS-232 port** to the DB9 plug. See the wiring below.

## Wiring

![RJ45 to DB9 RS-232 cable](docs/images/rs232-cable-rj45-db9.png)

| Inverter RJ45 pin | Typical wire colour | DB9 pin | Signal |
|---|---|---|---|
| 1 | white/orange | 2 | inverter TXD to computer RXD |
| 2 | blue | 3 | inverter RXD from computer TXD |
| 8 | white/green | 5 | ground |

Settings: **2400 baud, 8 data bits, no parity, 1 stop bit, no flow control.**

The pinout comes from the generic Voltronic protocol document for this inverter family. Wire colours differ between cables, so check them with a meter. The drawing is ours; the SVG source is in `docs/images/`.

**Test the adapter first, without the inverter.** Short DB9 pins 2 and 3 together and run `screen /dev/cu.usbserial-XXXX 2400` (on Linux, `/dev/ttyUSB0`). Letters you type should appear on screen. Remove the short and they should stop. Quit with Ctrl-A, then K, then Y. Never type into the terminal while the inverter is connected.

## Quick start

```bash
git clone https://github.com/Terramadas/Xunzel-RS232-Protocol.git
cd Xunzel-RS232-Protocol
python3 xunzel_readonly.py
```

You get a menu. Pick a number:

```
==== Xunzel IXS-ON 7200: READ-ONLY tool ====
  1  Quick status (mode, live values, warnings, flags)
  2  Live values once (QPIGS)
  3  Ratings and current settings (QPIRI)
  4  Setting flags (QFLAG)
  5  Warnings and faults (QPIWS)
  6  Serial number and firmware (QID, QVFW, QVFW2)
  7  Default settings (QDI, read only)
  8  Every read-only command in the manual
  9  Watch live values repeatedly (Ctrl-C to stop)
 10  Log live values to a CSV file (Ctrl-C to stop)
 11  Self-test (CRC + safety checks, no inverter needed)
 12  List the allowed commands
  p  Choose serial port / baud rate
  0  Quit
```

The script finds the USB serial port by itself (`/dev/cu.usbserial*` on macOS, `/dev/ttyUSB*` on Linux). Use `p` to pick another one. On Linux you may need to add your user to the `dialout` group.

You can also skip the menu: `python3 xunzel_readonly.py QPIGS`, `python3 xunzel_readonly.py --list`, `python3 xunzel_readonly.py --selftest`. Everything is also written to `xunzel_readonly.log` in the current folder, which is ignored by git because it contains your inverter's serial number.

A real example of the output is in [`examples/sample-output.txt`](examples/sample-output.txt). The first lines of a live-values reading look like this:

```
> QPIGS  (reply in 0.49 s)
  CRC : OK
   3  AC output voltage                                          230.0     V
   6  AC output active power                                     0081      W
   9  Battery voltage                                            54.10     V
  11  Battery capacity                                           099       %
  14  PV input voltage 1                                         273.1     V
  20  PV charging power [not in this manual]                     00073     W
```

## What you can read

| Command | What it gives you |
|---|---|
| `QPIGS` | Live values: grid and output voltage, load, battery voltage and charge, PV voltage and power, status bits |
| `QMOD` | Operating mode (battery, line, standby, fault, ...) |
| `QPIWS` | Warning and fault bits |
| `QPIRI` | Ratings and current settings |
| `QFLAG` | Which options are switched on or off |
| `QDI` | The default settings (this only reads them; it does not apply them) |
| `QID`, `QVFW` | Serial number, firmware version |
| `QET`, `QLT` | Total PV energy generated / total load energy consumed, all-time (Wh) |
| `QED`, `QEM`, `QEY` | PV energy generated for one day / month / year (Wh) |
| `QLD`, `QLM`, `QLY` | Load energy consumed for one day / month / year (Wh) |

The energy commands take a date as an argument (e.g. `QED20261124`, `QEY2026`) instead of being
fixed strings; the tool builds the right frame and CRC for any date you ask for.

Full details, byte-by-byte frames and field tables are in **[docs/PROTOCOL.md](docs/PROTOCOL.md)**.

## How read-only is enforced

1. **Whitelist, not blacklist.** The script can only build frames for the fixed list of query commands. Anything else is refused before the serial port is opened. Every allowed command starts with `Q`.
2. **One place writes to the port,** and it checks the whitelist itself. There is no option to switch this off.
3. **No typing into the menu.** You pick numbers; you never enter a command.
4. **Self-test.** `--selftest` checks the CRC against known values and real replies, and checks that setting commands (and typos of query commands) are refused.
5. **Reply checking.** Only replies with the right shape and a matching CRC are accepted.

If you write your own logger, the same rules apply. See [docs/PROTOCOL.md](docs/PROTOCOL.md#writing-your-own-logger-safely).

## What we found on this inverter

The Xunzel talks the common Voltronic/Axpert "PI30" protocol, but not exactly the way the generic 2014 protocol document describes:

- **Works:** `QMOD`, `QPIGS`, `QPIWS`, `QFLAG`, `QPIRI`, `QDI`, `QID`, `QVFW`.
- **Answers NAK (not supported):** `QPI` and `QVFW2`. Do not rely on `QPI` to detect the protocol.
- **More fields than documented:** `QPIGS` returns 21 fields (the document describes 17), `QPIRI` 28 (document: 25), `QDI` 26 (document: 25), and `QPIWS` 36 characters (document: 32). The extra fields are listed in the protocol document, with their likely meaning marked as unconfirmed.
- **Reply times:** 0.05 to 0.5 seconds. Polling `QPIGS` every 10 seconds is comfortable.
- **Pre-configured for the batteries:** the battery voltages and charge settings in the inverter differ from the factory defaults that `QDI` reports, as you would expect if the installer set them up for the lithium batteries. The inverter also reports battery type code 8, which the generic document does not describe. On this kit the inverter menu shows battery type **LIb** (lithium battery with communication), so 8 very likely means LIb. The batteries (2 x Xunzel SOLARX-Lithium WALL2 10 kWh) talk to the inverter over a separate RS485 link, which this project never touches. Details in [docs/PROTOCOL.md](docs/PROTOCOL.md#10-the-battery-and-the-lib-setting).
- **Off-grid:** with no grid connected, `QPIWS` always reports `LINE_FAIL`. That is normal.
- **PV voltage matches the leaflet:** the PV input voltage reads about 270 to 280 V in daylight, which fits seven 425 W panels per string as drawn in the leaflet (Voc about 295 V).
- **Energy totals exist too, undocumented:** besides the live values, the inverter answers eight more commands — `QET`/`QLT` for all-time PV/load energy, and date-based `QED`/`QEM`/`QEY` (PV) and `QLD`/`QLM`/`QLY` (load) for a given day, month or year. None of these are in the 2014 generic document; we found them by matching the inverter's own `dAY`/`MON`/`YEA`/`tOL` display screens against a test log, and cross-checked against the paper manual. The reply is an 8-digit number in Wh. We have not fully confirmed the scale on the day-period fields (`QED`/`QLD`) — verify against your own display before relying on them for anything precise. Details in [docs/PROTOCOL.md](docs/PROTOCOL.md#68-energy-totals-qet-qlt-qed-qem-qey-qld-qlm-qly-verified).
- **Two LCD menu items to leave alone:** the paper manual lists Program 37 ("reset all stored PV generated power and output load energy") and Program 93 ("erase all data log"). Neither is reachable over RS-232 — there is no way to send them by accident with this tool — but don't navigate into or confirm them on the front panel, since they would wipe the very totals above. Full menu reference: [docs/MANUAL-LCD-SETTING.md](docs/MANUAL-LCD-SETTING.md).

## Ideas for later

- A small always-on logger (Arduino Ethernet or Raspberry Pi with a MAX3232 level shifter) that stores `QPIGS` readings and serves them to a NAS or Home Assistant. The CSV format of `--csv` is the planned log format.
- The kit has two PV inputs (PV1 and PV2). Newer Voltronic documents describe a command for the second one; it is not in the document we used, so we have not tried it.
- The LCD's USB Function Setting menu can export the inverter's data log straight to a USB flash drive — a fully local, non-cloud way to get the full history off the inverter without polling the energy commands at all. We have not tried this ourselves yet. See [docs/MANUAL-LCD-SETTING.md](docs/MANUAL-LCD-SETTING.md#1-usb-function-setting).

Reports from other Xunzel or Voltronic-family inverters are welcome. If you share output, please remove your serial number first.

## Files

| Path | Purpose |
|---|---|
| `xunzel_readonly.py` | The read-only tool with menu |
| `docs/PROTOCOL.md` | Protocol reference: frames, CRC, commands, field tables |
| `docs/MANUAL-LCD-SETTING.md` | Front-panel LCD menu reference, Programs 00-99, transcribed from the paper manual |
| `index.html` | The same story as a web page (for GitHub Pages) |
| `docs/images/` | Wiring leaflet, cable drawing (PNG and SVG) |
| `examples/sample-output.txt` | Real output, serial number removed |

## Related work and sources

We are not the first to look at this protocol family. Independent sources that we found useful, and that agree with what we measured:

- **[Voltronic RS232 Protocol document, HS/MS/MSX, 2014-08-22](https://dwaves.de/wp-content/uploads/2023/06/Voltronic_Auslesen_Protocoll_HS_MS_MSX_RS232_Protocol_20140822_after_current_upgrade.pdf)** — the generic protocol document this project is checked against throughout `docs/PROTOCOL.md`.
- **[dwaves.de: WatchPower and Voltronic/MasterPower inverters on GNU/Linux](https://dwaves.de/2023/06/27/web-power-statistics-for-masterpower-voltronic-how-to-run-watchpower-software-gnu-linux-debian-reading-writing-good-quality-voltronic-aka-masterpower-pms-5k-48top-off-grid-aka-axpert-mks-ii-5k-ak/)** — a detailed write-up of reading a Voltronic/MasterPower inverter over USB/serial on Linux. It independently confirms the same CRC routine (CRC-16 with the 0x1021 polynomial, bumping any `0x28`/`0x0D`/`0x0A` byte by one) and the same 2400 8N1 serial settings. It also notes that different inverter firmware versions can return different field counts for the same command, which matches what we see between the generic document and this Xunzel (more fields in `QPIGS`, `QPIRI`, `QDI` and `QPIWS`). Worth reading if you want to see the wired, desktop WatchPower software in use on Linux rather than the phone app; that desktop tool talks to the inverter over a cable and, as far as that page shows, keeps its logs and charts local.
- **[manio/skymax-demo](https://github.com/manio/skymax-demo)** — an open-source C poller for the same protocol family, with raw-command support. A useful second implementation to compare frames against.
- **[Skyboo: Monitoring a Voltronic Axpert MEX inverter under Linux](https://skyboo.net/2017/03/monitoring-voltronic-power-axpert-mex-inverter-under-linux/)** — another independent write-up of the same protocol family.

If you know of other Xunzel-specific or IXS-ON-specific resources, open an issue or a pull request.

## Search terms

Xunzel IXS-ON 7200 RS232, Xunzel inverter RS-232 protocol, Xunzel PACK ZERO+ monitoring, IXS-ON-7200W-48V serial port, Xunzel inverter logging, Xunzel SOLARX-Lithium WALL2 inverter communication, Voltronic Axpert compatible Xunzel, QPIGS QPIRI QMOD Xunzel, Leroy Merlin Xunzel kit, WatchPower alternative.

## Licence

MIT, see [LICENSE](LICENSE).
