# Protocol reference: Xunzel IXS-ON 7200 over RS-232 (read-only)

What this covers: the query commands that work on the Xunzel IXS-ON 7200 W inverter (PACK ZERO+ AX 490 L kit, firmware `VERFW:00069.07`), how to build and check a frame, and how to read each reply.

The inverter speaks the Voltronic/Axpert "PI30" family of protocols. The general layout comes from a widely circulated Voltronic RS-232 protocol document for the HS/MS/MSX series (2014), which we call "the generic document" below. We do not redistribute it. Everything here was checked against a real inverter on 2026-11-23.

**Golden rule: only send the query commands in section 5. Never send a setting command (section 7).**

Status labels:

- **VERIFIED**: seen working on the Xunzel IXS-ON 7200.
- **GENERIC**: described in the generic document, not seen on this inverter.
- **UNDOCUMENTED**: the inverter sends it, but the generic document does not describe it. Any meaning given is borrowed from other published PI30 documents and is a guess until confirmed.

---

## 1. Link

| Item | Value |
|---|---|
| Connector on the inverter | RJ45, RS-232 |
| Serial settings | 2400 baud, 8N1, no flow control (VERIFIED) |
| Level | RS-232. A microcontroller or Raspberry Pi needs a level shifter such as a MAX3232 |
| Cable | RJ45 pin 1 = inverter TXD, pin 2 = inverter RXD, pin 8 = GND; straight through to DB9 pins 2, 3, 5. See the [README](../README.md#wiring) |

## 2. Frame format

**You send:** command text, then 2 CRC bytes (high byte first), then `0x0D` (carriage return).

**The inverter answers:** `(`, the data, 2 CRC bytes, then `0x0D`.

Example (VERIFIED): `QPIGS` goes out as `51 50 49 47 53 b7 a9 0d`.

The CRC of a reply covers every byte from the opening `(` up to, but not including, the two CRC bytes and the final `0x0D`. Reject any reply that does not start with `(`, does not end with `0x0D`, or has the wrong CRC.

A reply of `(NAK` plus a valid CRC means "command not supported". It is harmless.

## 3. CRC

CRC-16/XMODEM: polynomial `0x1021`, start value `0`, no reflection. One extra rule: if either CRC byte comes out as `0x28` (`(`), `0x0D` (CR) or `0x0A` (LF), it is increased by one, so a CRC byte can never be mistaken for a frame marker.

Reference code in C (checked against all the commands below and against real replies):

```c
#include <stdint.h>

uint16_t crc_update(uint16_t crc, uint8_t b) {
  crc ^= (uint16_t)b << 8;
  for (uint8_t i = 0; i < 8; i++)
    crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  return crc;
}

uint16_t crc_final(uint16_t crc) {
  uint8_t hi = crc >> 8, lo = crc & 0xFF;
  if (hi == 0x28 || hi == 0x0D || hi == 0x0A) hi++;
  if (lo == 0x28 || lo == 0x0D || lo == 0x0A) lo++;
  return ((uint16_t)hi << 8) | lo;
}
```

Start with `crc = 0`, call `crc_update` for each byte, then `crc_final`. The same logic in Python is in `xunzel_readonly.py` (`voltronic_crc`).

## 4. Ready-made query frames

| Command | Bytes to send | Status |
|---|---|---|
| `QPI` | 51 50 49 be ac 0d | VERIFIED: answers NAK |
| `QID` | 51 49 44 d6 ea 0d | VERIFIED |
| `QVFW` | 51 56 46 57 62 99 0d | VERIFIED |
| `QVFW2` | 51 56 46 57 32 c3 f5 0d | VERIFIED: answers NAK |
| `QPIRI` | 51 50 49 52 49 f8 54 0d | VERIFIED |
| `QFLAG` | 51 46 4c 41 47 98 74 0d | VERIFIED |
| `QPIGS` | 51 50 49 47 53 b7 a9 0d | VERIFIED |
| `QMOD` | 51 4d 4f 44 49 c1 0d | VERIFIED |
| `QPIWS` | 51 50 49 57 53 b4 da 0d | VERIFIED |
| `QDI` | 51 44 49 71 1b 0d | VERIFIED |
| `QMCHGCR` | 51 4d 43 48 47 43 52 d8 55 0d | GENERIC |
| `QMUCHGCR` | 51 4d 55 43 48 47 43 52 26 34 0d | GENERIC |
| `QBOOT` | 51 42 4f 4f 54 0b 88 0d | GENERIC (may answer NAK) |
| `QOPM` | 51 4f 50 4d a5 c5 0d | GENERIC (documented for other models; may answer NAK) |
| `QPGS0` | 51 50 47 53 30 3f da 0d | GENERIC (parallel units; may answer NAK) |
| `QET` | 51 45 54 81 b6 0d | VERIFIED: total PV energy, all-time |
| `QLT` | 51 4c 54 3b 2e 0d | VERIFIED: total load energy, all-time |
| `QED20261124` | 51 45 44 32 30 32 36 31 31 32 34 f2 45 0d | VERIFIED: PV energy for 2026-11-24 (pattern `QED` + `YYYYMMDD`) |
| `QEM202611` | 51 45 4d 32 30 32 36 31 31 60 fc 0d | VERIFIED: PV energy for 2026-11 (pattern `QEM` + `YYYYMM`) |
| `QEY2026` | 51 45 59 32 30 32 36 f7 ef 0d | VERIFIED: PV energy for 2026 (pattern `QEY` + `YYYY`) |
| `QLD20261124` | 51 4c 44 32 30 32 36 31 31 32 34 d7 4b 0d | VERIFIED: load energy for 2026-11-24 (pattern `QLD` + `YYYYMMDD`) |
| `QLM202611` | 51 4c 4d 32 30 32 36 31 31 39 f5 0d | VERIFIED: load energy for 2026-11 (pattern `QLM` + `YYYYMM`) |
| `QLY2026` | 51 4c 59 32 30 32 36 bf 0e 0d | VERIFIED: load energy for 2026 (pattern `QLY` + `YYYY`) |

The six date-based commands are not fixed strings: the CRC bytes shown are only valid for that
exact date argument, because the CRC is computed over the whole frame including the digits.
`xunzel_readonly.py` computes the right CRC for whatever date you ask for; see
`energy_commands_for_today()`.

## 5. The read-only commands

| Command | Returns |
|---|---|
| `QPI` | Protocol ID. The generic document says `(PI30`; this inverter answers `(NAK` |
| `QID` | Serial number, 14 digits |
| `QVFW` | Main firmware, e.g. `(VERFW:00069.07` = series 00069, version 07 |
| `QVFW2` | Second CPU firmware. This inverter answers NAK |
| `QPIGS` | Live values (section 6.1) |
| `QMOD` | Operating mode (6.2) |
| `QPIWS` | Warning and fault bits (6.3) |
| `QFLAG` | Which options are on or off (6.4) |
| `QPIRI` | Ratings and current settings (6.5) |
| `QDI` | Factory default settings (6.6). It only reports them; it does not apply them |
| `QMCHGCR`, `QMUCHGCR` | Lists of selectable charging currents |
| `QBOOT`, `QOPM`, `QPGSn` | Extra queries from the generic document; not needed for monitoring |
| `QET`, `QLT` | All-time PV energy generated / load energy consumed, in Wh (section 6.8) |
| `QED`, `QEM`, `QEY` | PV energy generated for one day / month / year, Wh (section 6.8) |
| `QLD`, `QLM`, `QLY` | Load energy consumed for one day / month / year, Wh (section 6.8) |

Other query commands exist in newer PI30 documents (for example for the second PV input). They are not in the generic document and have not been tried here.

---

## 6. Reading the replies

### 6.1 QPIGS: live values (VERIFIED, 21 fields)

A real reply:

`(000.0 00.0 230.0 50.0 0092 0081 001 449 54.10 000 099 0042 00.2 273.1 00.00 00000 00010000 00 00 00073 010`

| # | Field | Unit | Sample | Source |
|---|---|---|---|---|
| 1 | Grid voltage | V | 000.0 | generic |
| 2 | Grid frequency | Hz | 00.0 | generic |
| 3 | AC output voltage | V | 230.0 | generic |
| 4 | AC output frequency | Hz | 50.0 | generic |
| 5 | AC output apparent power | VA | 0092 | generic |
| 6 | AC output active power | W | 0081 | generic |
| 7 | Output load (the larger of W% and VA%) | % | 001 | generic |
| 8 | DC bus voltage | V | 449 | generic |
| 9 | Battery voltage | V | 54.10 | generic |
| 10 | Battery charging current | A | 000 | generic |
| 11 | Battery capacity | % | 099 | generic |
| 12 | Heat sink temperature | see note | 0042 | generic |
| 13 | PV input current for battery | A | 00.2 | generic |
| 14 | PV input voltage 1 | V | 273.1 | generic |
| 15 | Battery voltage from the solar charger | V | 00.00 | generic |
| 16 | Battery discharge current | A | 00000 | generic |
| 17 | Device status, bits b7..b0 | bits | 00010000 | generic |
| 18 | Battery voltage offset for fans on | | 00 | UNDOCUMENTED |
| 19 | EEPROM version | | 00 | UNDOCUMENTED |
| 20 | PV charging power | W | 00073 | UNDOCUMENTED |
| 21 | Device status 2, bits b10..b8 | bits | 010 | UNDOCUMENTED |

Notes:

- Field 12: the generic document calls it a raw sensor value for smaller models. On this inverter it looks like degrees Celsius (42). Check it against the display.
- Field 7: 92 VA of 7200 VA is 1.3 percent, shown as `001`. That fits the 7200 VA rating.
- Fields 18 to 21 are extra. Field 20 looks right: 73 W of PV power at about 273 V and 0.2 to 0.3 A.
- With the battery full, PV power simply follows the load, so low PV power in daylight is normal.

**Field 17, device status (first character is b7):**

| Bit | Meaning |
|---|---|
| b7 | add SBU priority version |
| b6 | configuration changed |
| b5 | solar charger firmware updated |
| b4 | load is on |
| b3 | battery voltage steady while charging |
| b2 | charging on |
| b1 | charging from solar on |
| b0 | charging from AC on |

The sample `00010000` means only "load on".

**Field 21, status 2 (first character is b10, UNDOCUMENTED here):** b10 floating charge, b9 switch on, b8 dustproof kit installed (meanings from other PI30 documents). The sample `010` means "switch on".

### 6.2 QMOD: operating mode (VERIFIED)

| Reply | Mode |
|---|---|
| `(P` | Power on |
| `(S` | Standby |
| `(L` | Line (grid) |
| `(B` | Battery |
| `(F` | Fault |
| `(H` | Power saving |

### 6.3 QPIWS: warnings and faults (VERIFIED)

The generic document describes 32 characters, one per bit `a0` to `a31`; `1` means active. This inverter sends **36**; the 4 extra characters are not documented (all 0 so far).

| Bit | Meaning | Bit | Meaning |
|---|---|---|---|
| a0 | reserved | a16 | overload |
| a1 | inverter fault | a17 | EEPROM fault |
| a2 | bus over | a18 | inverter over current |
| a3 | bus under | a19 | inverter soft start fail |
| a4 | bus soft start fail | a20 | self test fail |
| a5 | line fail | a21 | output DC voltage over |
| a6 | output voltage short | a22 | battery open |
| a7 | inverter voltage too low | a23 | current sensor fail |
| a8 | inverter voltage too high | a24 | battery short |
| a9 | over temperature | a25 | power limit |
| a10 | fan locked | a26 | PV voltage high |
| a11 | battery voltage high | a27 | MPPT overload fault |
| a12 | battery low alarm | a28 | MPPT overload warning |
| a13 | reserved | a29 | battery too low to charge |
| a14 | battery under shutdown | a30, a31 | reserved |
| a15 | reserved | | |

In the generic document, a9, a10, a11 and a16 count as faults when a1 is also set and as warnings otherwise.

**Off-grid note:** with no grid connected the inverter sets `a5` (line fail) all the time. That is expected and not a fault.

### 6.4 QFLAG: options on or off (VERIFIED)

The reply looks like `(ExyzDabjkuv`. Letters after `E` are enabled, letters after `D` are disabled. This inverter sends the letters in lower case.

| Letter | Option |
|---|---|
| a | buzzer |
| b | overload bypass |
| j | power saving |
| k | LCD returns to the default page after 1 minute |
| u | overload restart |
| v | over-temperature restart |
| x | LCD backlight |
| y | alarm when the primary source is interrupted |
| z | fault code record |

### 6.5 QPIRI: ratings and current settings (VERIFIED, 28 fields)

A real reply:

`(230.0 31.3 230.0 50.0 31.3 7200 7200 48.0 47.0 46.4 57.6 57.6 8 30 010 0 0 2 9 01 0 0 54.0 0 1 480 0 000`

| # | Field | Sample |
|---|---|---|
| 1 | Grid rating voltage (V) | 230.0 |
| 2 | Grid rating current (A) | 31.3 |
| 3 | AC output rating voltage (V) | 230.0 |
| 4 | AC output rating frequency (Hz) | 50.0 |
| 5 | AC output rating current (A) | 31.3 |
| 6 | AC output rating apparent power (VA) | 7200 |
| 7 | AC output rating active power (W) | 7200 |
| 8 | Battery rating voltage (V) | 48.0 |
| 9 | Battery re-charge voltage (V) | 47.0 |
| 10 | Battery under voltage (V) | 46.4 |
| 11 | Battery bulk voltage (V) | 57.6 |
| 12 | Battery float voltage (V) | 57.6 |
| 13 | Battery type | 8 |
| 14 | Max AC charging current (A) | 30 |
| 15 | Max charging current (A) | 010 |
| 16 | Input voltage range (0 appliance, 1 UPS) | 0 |
| 17 | Output source priority (0 utility first, 1 solar first, 2 SBU first) | 0 |
| 18 | Charger source priority (0 utility first, 1 solar first, 2 solar and utility, 3 solar only) | 2 |
| 19 | Parallel max number | 9 |
| 20 | Machine type (00 grid tie, 01 off grid, 10 hybrid) | 01 |
| 21 | Topology (0 transformerless, 1 transformer) | 0 |
| 22 | Output mode (00 single) | 0 |
| 23 | Battery re-discharge voltage (V) | 54.0 |
| 24 | PV OK condition for parallel | 0 |
| 25 | PV power balance (0 max current, 1 max power) | 1 |
| 26 | UNDOCUMENTED, probably max charging time at constant voltage, in minutes | 480 |
| 27 | UNDOCUMENTED, probably operation logic | 0 |
| 28 | UNDOCUMENTED, probably max discharging current | 000 |

Notes:

- The generic document lists battery type 0 (AGM), 1 (flooded) and 2 (user). This inverter reports **8**. On this kit the inverter's own menu (PROGRAM 05) is set to **LIb**, "LIb-protocol compatible battery", so 8 very likely means LIb. That is our reading, not confirmed by Xunzel. See [section 10](#10-the-battery-and-the-lib-setting).
- The rated 7200 VA / 7200 W and machine type `01` (off grid) match the product.
- The battery voltages (57.6 V bulk and float, 46.4 V under voltage) look like a 16-cell lithium pack, but that is an inference.

### 6.6 QDI: default settings (VERIFIED, 26 fields)

A real reply:

`(230.0 50.0 0030 44.0 54.0 56.4 46.0 60 0 0 2 0 0 0 0 0 1 1 1 0 1 0 54.0 0 1 224`

Field order: AC output voltage, output frequency, max AC charging current, battery under voltage, float voltage, bulk voltage, re-charge voltage, max charging current, AC input voltage range, output source priority, charger source priority, battery type, buzzer, power saving, overload restart, over-temperature restart, LCD backlight, alarm on primary interrupt, fault code record, overload bypass, LCD return to default page, output mode, battery re-discharge voltage, PV OK condition, PV power balance. Field 26 (`224`) is undocumented.

Comparing `QDI` with `QPIRI` on this kit shows what Xunzel changed from the generic factory defaults:

| Setting | Default | In this kit |
|---|---|---|
| Battery under voltage | 44.0 V | 46.4 V |
| Battery re-charge voltage | 46.0 V | 47.0 V |
| Bulk voltage | 56.4 V | 57.6 V |
| Float voltage | 54.0 V | 57.6 V |
| Max charging current | 60 A | 10 A |
| Battery type | 0 | 8 |

These are the sort of values set for a lithium battery. They are exactly the settings we do not touch.

### 6.7 QID and QVFW (VERIFIED)

`QID` returns `(` plus 14 digits. `QVFW` returns `(VERFW:NNNNN.NN`. Keep your serial number out of anything you publish.

### 6.8 Energy totals: QET, QLT, QED, QEM, QEY, QLD, QLM, QLY (VERIFIED)

None of these are in the 2014 generic document. We found them by matching the inverter's own
front-panel screens — reached by pressing the display button repeatedly until `dAY`, `MON`,
`YEA` and `tOL` appear — against a test log of RS-232 replies, then cross-checking the LCD
menu's energy-related entries in the paper manual.

| Command | Argument | Returns |
|---|---|---|
| `QET` | none | Total PV energy ever generated, in Wh (matches the `tOL` PV screen) |
| `QLT` | none | Total load (output) energy ever consumed, in Wh (matches the `tOL` load screen) |
| `QED` | `YYYYMMDD` | PV energy generated on that calendar day, in Wh (matches the `dAY` PV screen) |
| `QEM` | `YYYYMM` | PV energy generated in that calendar month, in Wh (matches the `MON` PV screen) |
| `QEY` | `YYYY` | PV energy generated in that calendar year, in Wh (matches the `YEA` PV screen) |
| `QLD` | `YYYYMMDD` | Load energy consumed on that calendar day, in Wh |
| `QLM` | `YYYYMM` | Load energy consumed in that calendar month, in Wh |
| `QLY` | `YYYY` | Load energy consumed in that calendar year, in Wh |

The reply format is `(` + 8 digits + CRC + CR, e.g. `(00724100` for `QET`. On our test day
(2026-11-24) `QEY2026` and `QET` returned the same value (`00724100`), which makes sense: the
inverter was commissioned this year, so "this year" and "all-time" are currently identical. We
have **not fully confirmed the unit scale on the day-period fields** (`QED`/`QLD`) against the
display — the month and year fields matched the `MON`/`YEA`/`tOL` screens directly in Wh, but we
did not have a second day's worth of display readings to triple-check `dAY` the same way. Treat
`QED`/`QLD` as Wh for now, and verify against your own display before relying on them for
anything precise.

Because these commands take a date as an argument, the CRC is different for every date — there
is no single fixed frame to memorize. `xunzel_readonly.py` builds the correct frame and CRC for
you; see `energy_commands_for_today()` and menu option 8 / CLI `--list`.

---

## 7. Commands we never send

The generic document also lists **setting commands**. They change the inverter, so they are not in the tool and must not be added. None of them start with `Q`.

| Group | What it can change |
|---|---|
| `PE...` / `PD...` | switch options on or off (buzzer, bypass, power saving, backlight, restarts, alarm, fault record) |
| `PF` | **resets every setting to the factory default** |
| `F50`, `F60` | output frequency |
| `POP..` | output source priority |
| `PBCV`, `PBDV` | battery re-charge and re-discharge voltage |
| `PCP` | charger source priority |
| `PGR` | grid working range |
| `PBT` | battery type |
| `PSDV`, `PCVV`, `PBFT` | battery cut-off, bulk and float voltage |
| `PPVOKC`, `PSPB` | PV OK condition, solar power balance |
| `MCHGC`, `MUCHGC`, `MNCHGC` | maximum charging currents |
| `POPM`, `PPCP` | output mode, parallel charger priority |

Wrong battery voltages or charge limits can damage a battery, and changing settings may affect your warranty. Change settings only on the inverter itself, following the manufacturer's instructions.

**Also never confirm these two items on the front-panel LCD menu.** They are not RS-232 commands
at all — there is no way to send them over the serial link, by accident or otherwise — but they
are destructive LCD-menu programs found in the paper manual, and they would erase exactly the
data that `QET`/`QLT`/`QED`/`QEM`/`QEY`/`QLD`/`QLM`/`QLY` read back:

| Program | What it does |
|---|---|
| Program 37 | Resets all stored PV generated power and output load energy totals to zero |
| Program 93 | Erases the entire data log |

If you want a local, non-cloud way to pull the full history off the inverter instead of
re-reading totals over RS-232, the LCD's USB Function Setting menu can export the data log to a
USB flash drive — see the "Ideas for later" section of the README.

---

## 8. Writing your own logger safely

If you build your own logger (Arduino, Raspberry Pi, ESP32, ...), keep it read-only the same way:

1. **Fixed frames only.** Store the exact bytes from section 4 as constants. Never build a command from text, a web request or a serial console. At start-up, check that every frame begins with `Q` (0x51).
2. **No path from the network to the serial port.** A web page or API may only return stored data. It must never forward a request or a received byte to the inverter.
3. **Careful with shared serial lines.** Some boards (for example the Arduino Ethernet R3) share the single hardware UART between the programming header and your RS-232 module. Anything typed into a serial monitor would then reach the inverter. Disconnect the module when uploading or debugging.
4. **Validate every reply:** starts with `(`, ends with `0x0D`, CRC matches. Ignore anything else.
5. **One command at a time.** Clear the input buffer, send, wait for the reply (a 5 second timeout is plenty), then send the next. Do not retry in a tight loop after a NAK or a timeout; wait for the next cycle.

A sensible polling plan (our suggestion): `QPIGS` every 10 to 30 seconds, `QMOD` and `QPIWS` about once a minute, `QPIRI`, `QFLAG`, `QID` and `QVFW` once at start-up and then daily.

Measured reply times: `QMOD` 0.05 s, `QFLAG` 0.1 s, `QPIWS` 0.2 s, `QDI` 0.4 s, `QPIGS` and `QPIRI` 0.5 s.

A simple log line, the same as the tool's `--csv` output: `2026-11-23T14:25:52Z,QPIGS,000.0 00.0 230.0 ...` (UTC time, command, reply without the `(`, the CRC and the final `0x0D`). Storing the raw text keeps the logger simple; the fields can be split later on a bigger machine.

---

## 9. Differences from the generic document (summary)

| Topic | Generic document | Xunzel IXS-ON 7200 |
|---|---|---|
| CRC method and rule | CRC-16/XMODEM with the `(`/CR/LF rule | The same; all replies validate |
| Serial settings | 2400 8N1 | Confirmed |
| `QPI` | `(PI30` | `(NAK` |
| `QVFW2` | second firmware | `(NAK` |
| `QPIGS` | 17 fields | 21 fields |
| `QPIRI` | 25 fields | 28 fields, battery type 8 |
| `QDI` | 25 fields | 26 fields |
| `QPIWS` | 32 characters | 36 characters |
| `QFLAG` letters | upper case | lower case |
| Energy totals (`QET`/`QLT`/`QED`/`QEM`/`QEY`/`QLD`/`QLM`/`QLY`) | not in the generic document | VERIFIED, found via the LCD `dAY`/`MON`/`YEA`/`tOL` screens and the paper manual |
| Models covered | HS, MS, MSX (1 to 5 kVA) | The 7200 W is not listed, so treat every label as likely until checked |

---

## 10. The battery and the LIb setting

This section comes from the kit's own paper manuals and a photo of the battery specification page. It is not read over RS-232.

**Battery in the kit:** 2 x Xunzel SOLARX-Lithium WALL2 10KWH-51.2V-200A (model code SXLW210K).

| Battery specification | Value |
|---|---|
| Nominal voltage / capacity / energy | 51.2 V / 200 Ah / 10240 Wh |
| Max charging and discharging current | 200 A each |
| Charging voltage | 55.2 to 57.6 V |
| End of discharge voltage | 44.8 V (backup use), 48 V (cycle use) |
| Operating temperature | charge 0 to +55 C, discharge -20 to +55 C (standard product) |
| Communication interface | RS485 and CAN |
| Parallel support | up to 6 |

**How the battery is connected:** battery 2 is linked to battery 1 with a data cable, and battery 1 is linked to the inverter. The manuals describe the link as RS485. This is a **separate port** from the RS-232 port used here, so this project never touches the battery link.

**Inverter setting:** on the inverter's menu, PROGRAM 05 (battery type) is set to **LIb**. The inverter menu text says that choosing LIb automatically sets programs 02, 26, 27 and 29 (in other Voltronic manuals these are max charging current, bulk voltage, float voltage and low DC cut-off voltage), so no further setting is needed.

**How this fits the QPIRI values:**

| QPIRI field | Value on this kit | Battery specification |
|---|---|---|
| Battery bulk voltage (11) | 57.6 V | top of the 55.2 to 57.6 V charging range |
| Battery float voltage (12) | 57.6 V | same |
| Battery under voltage (10) | 46.4 V | between 44.8 V and 48 V end of discharge |
| Max charging current (15) | 10 A | batteries allow 200 A each |

The voltages sit inside the battery's own limits. The 10 A figure looks low for two 200 A batteries. With a communicating lithium battery the battery's management system normally sets the real charge limit over the data cable, so 10 A may only be a placeholder. We have not confirmed this. If you want to check, watch `QPIGS` field 10 (battery charging current) and field 20 (PV charging power) in strong sun with a part-empty battery. We read it; we do not change it.
