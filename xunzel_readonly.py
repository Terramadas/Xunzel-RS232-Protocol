#!/usr/bin/env python3
"""
xunzel_readonly.py - READ-ONLY RS-232 query tool for the Xunzel IXS-ON 7200 inverter
(Voltronic "PI30"-style protocol). https://github.com/Terramadas/Xunzel-RS232-Protocol

SAFETY: this tool can only send the query commands listed in READ_ONLY below
(all start with "Q"). Every other command, including every setting command,
is refused before anything is sent. There is no option to bypass this. The only
code that writes to the serial port is ReadOnlyLink.query(), and it checks the
whitelist itself. Not affiliated with Xunzel. MIT licence, use at your own risk.

Standard library only (no pyserial). Works on macOS and Linux.

Usage:
  python3 xunzel_readonly.py                      # opens the menu (just pick a number)
  python3 xunzel_readonly.py --menu               # same
  python3 xunzel_readonly.py QMOD QPIGS           # run chosen read-only commands directly
  python3 xunzel_readonly.py all                  # every read-only command, incl. energy totals
  python3 xunzel_readonly.py QET QLT QEY2026      # all-time + this-year PV energy totals (Wh)
  python3 xunzel_readonly.py --repeat 6 --every 10 QPIGS
  python3 xunzel_readonly.py --csv data.csv QPIGS # append UTC,command,raw payload
  python3 xunzel_readonly.py --list               # show the allowed commands
  python3 xunzel_readonly.py --selftest           # CRC + safety tests, no serial port needed
  python3 xunzel_readonly.py --port /dev/cu.usbserial-XXXX --baud 2400 QPIGS

Besides the fixed commands, six date-based energy totals are allowed:
QED<YYYYMMDD>, QEM<YYYYMM>, QEY<YYYY> (PV generated), and QLD/QLM/QLY (load
consumed) for the same periods, plus QET/QLT for all-time totals. See --list.

The menu only offers fixed read-only actions; you never type a command into it.
Everything printed is also appended to xunzel_readonly.log in the current folder.
"""
__version__ = "1.1.0"
import datetime
import glob
import os
import re
import select
import sys
import termios
import time
import tty

LOGFILE = "xunzel_readonly.log"

# ---------------------------------------------------------------------------
# The whitelist: every query command in the manual (section 2). Nothing else.
# ---------------------------------------------------------------------------
READ_ONLY = {
    "QPI":      "Protocol ID (this inverter answers NAK; not supported)",
    "QID":      "Serial number",
    "QVFW":     "Main CPU firmware version",
    "QVFW2":    "Second CPU firmware version (this inverter answers NAK)",
    "QPIRI":    "Rated information (ratings and current settings)",
    "QFLAG":    "Setting flags (enabled/disabled)",
    "QPIGS":    "General status: live values (voltages, power, battery, PV)",
    "QMOD":     "Operating mode",
    "QPIWS":    "Warning and fault status bits",
    "QDI":      "Default setting values (read only; does NOT change anything)",
    "QMCHGCR":  "List of selectable max charging currents",
    "QMUCHGCR": "List of selectable max utility charging currents",
    "QBOOT":    "DSP bootstrap flag (may be NAK)",
    "QOPM":     "Output mode (documented for 4000/5000; may be NAK)",
    "QET":      "Total PV energy generated, all-time (Wh)",
    "QLT":      "Total load (output) energy, all-time (Wh)",
}
QPGS_RE = re.compile(r"^QPGS[0-9]$")  # parallel info, per unit number (may be NAK)

# Energy-by-period queries: not fixed strings, each takes a date/month/year
# argument. Not in the generic 2014 protocol document; found on this inverter
# by comparing its front-panel "dAY/MON/YEA/tOL" screens against these replies.
QED_RE = re.compile(r"^QED\d{8}$")   # PV energy for one day, argument YYYYMMDD
QEM_RE = re.compile(r"^QEM\d{6}$")   # PV energy for one month, argument YYYYMM
QEY_RE = re.compile(r"^QEY\d{4}$")   # PV energy for one year, argument YYYY
QLD_RE = re.compile(r"^QLD\d{8}$")   # load energy for one day, argument YYYYMMDD
QLM_RE = re.compile(r"^QLM\d{6}$")   # load energy for one month, argument YYYYMM
QLY_RE = re.compile(r"^QLY\d{4}$")   # load energy for one year, argument YYYY
ENERGY_PATTERNS = [QPGS_RE, QED_RE, QEM_RE, QEY_RE, QLD_RE, QLM_RE, QLY_RE]
DEFAULT_SET = ["QMOD", "QPIGS", "QPIWS", "QFLAG"]


def is_allowed(cmd: str) -> bool:
    return cmd in READ_ONLY or any(p.match(cmd) for p in ENERGY_PATTERNS)


def refuse(cmd: str):
    kind = "a SETTING command" if not cmd.startswith("Q") else "not in the read-only list"
    sys.exit("REFUSED: %r is %s. This tool only sends read-only queries (see --list)." % (cmd, kind))


# ---------------------------------------------------------------------------
# Framing and CRC (identical to the manual's CRC.c)
# ---------------------------------------------------------------------------
def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def voltronic_crc(data: bytes) -> bytes:
    """CRC16-XMODEM; any CRC byte equal to '(' CR or LF is incremented by 1."""
    crc = crc16_xmodem(data)
    hi, lo = crc >> 8, crc & 0xFF
    if hi in (0x28, 0x0D, 0x0A):
        hi += 1
    if lo in (0x28, 0x0D, 0x0A):
        lo += 1
    return bytes([hi, lo])


def build_frame(cmd: str) -> bytes:
    if not is_allowed(cmd):
        refuse(cmd)
    raw = cmd.encode("ascii")
    frame = raw + voltronic_crc(raw) + b"\r"
    assert frame[:1] == b"Q", "internal safety check: frame must start with Q"
    assert frame.count(b"\r") == 1 and frame.endswith(b"\r")
    return frame


# ---------------------------------------------------------------------------
# Serial link: the only place that writes to the port
# ---------------------------------------------------------------------------
class ReadOnlyLink:
    def __init__(self, path: str, baud: int = 2400):
        self._fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        tty.setraw(self._fd)
        a = termios.tcgetattr(self._fd)
        a[2] &= ~(termios.PARENB | termios.CSTOPB | termios.CSIZE | termios.CRTSCTS)
        a[2] |= termios.CS8 | termios.CLOCAL | termios.CREAD
        a[4] = a[5] = getattr(termios, "B%d" % baud)
        a[6][termios.VMIN] = 0
        a[6][termios.VTIME] = 0
        termios.tcsetattr(self._fd, termios.TCSANOW, a)
        termios.tcflush(self._fd, termios.TCIOFLUSH)

    def query(self, cmd: str, timeout: float = 5.0):
        """Send one whitelisted query; return (raw_reply, seconds)."""
        frame = build_frame(cmd)            # refuses anything not whitelisted
        termios.tcflush(self._fd, termios.TCIFLUSH)
        t0 = time.time()
        os.write(self._fd, frame)
        buf = b""
        while time.time() - t0 < timeout:
            r, _, _ = select.select([self._fd], [], [], 0.1)
            if r:
                chunk = os.read(self._fd, 256)
                if chunk:
                    buf += chunk
                    if b"\r" in buf:
                        break
        return buf, time.time() - t0

    def close(self):
        os.close(self._fd)


# ---------------------------------------------------------------------------
# Decoders
# ---------------------------------------------------------------------------
QPIGS_FIELDS = [
    ("Grid voltage", "V"), ("Grid frequency", "Hz"), ("AC output voltage", "V"),
    ("AC output frequency", "Hz"), ("AC output apparent power", "VA"),
    ("AC output active power", "W"), ("Output load (max of W% / VA%)", "%"),
    ("BUS voltage", "V"), ("Battery voltage", "V"), ("Battery charging current", "A"),
    ("Battery capacity", "%"), ("Inverter heat sink temperature", "(degC? see manual note)"),
    ("PV input current for battery", "A"), ("PV input voltage 1", "V"),
    ("Battery voltage from SCC", "V"), ("Battery discharge current", "A"),
    ("Device status b7..b0", ""),
    ("Battery voltage offset for fans on [not in this manual]", ""),
    ("EEPROM version [not in this manual]", ""),
    ("PV charging power [not in this manual]", "W"),
    ("Device status 2 b10..b8 [not in this manual]", ""),
]
STATUS_BITS = ["add SBU priority version", "configuration changed", "SCC firmware updated",
               "load ON", "battery voltage steady while charging", "charging on",
               "SCC (solar) charging on", "AC charging on"]          # b7 .. b0
STATUS2_BITS = ["floating charge", "switch on", "dustproof installed"]  # b10 .. b8 (common PI30, not in this manual)
MODES = {"P": "Power on", "S": "Standby", "L": "Line (grid)", "B": "Battery",
         "F": "Fault", "H": "Power saving"}
QPIWS_BITS = ["Reserved", "Inverter fault", "Bus over", "Bus under", "Bus soft fail", "LINE_FAIL",
              "OPV short", "Inverter voltage too low", "Inverter voltage too high", "Over temperature",
              "Fan locked", "Battery voltage high", "Battery low alarm", "Reserved",
              "Battery under shutdown", "Reserved", "Over load", "EEPROM fault",
              "Inverter over current", "Inverter soft fail", "Self test fail", "OP DC voltage over",
              "Battery open", "Current sensor fail", "Battery short", "Power limit",
              "PV voltage high", "MPPT overload fault", "MPPT overload warning",
              "Battery too low to charge", "Reserved", "Reserved"]
QFLAG_NAMES = {"A": "Buzzer", "B": "Overload bypass", "J": "Power saving", "K": "LCD return to default page (1 min)",
               "U": "Overload restart", "V": "Over-temperature restart", "X": "LCD backlight",
               "Y": "Alarm when primary source interrupted", "Z": "Fault code record"}
QPIRI_FIELDS = ["Grid rating voltage (V)", "Grid rating current (A)", "AC output rating voltage (V)",
                "AC output rating frequency (Hz)", "AC output rating current (A)",
                "AC output rating apparent power (VA)", "AC output rating active power (W)",
                "Battery rating voltage (V)", "Battery re-charge voltage (V)", "Battery under voltage (V)",
                "Battery bulk voltage (V)", "Battery float voltage (V)",
                "Battery type (0 AGM, 1 Flooded, 2 User; other values not in this manual)", "Current max AC charging current (A)",
                "Current max charging current (A)", "Input voltage range (0 Appliance, 1 UPS)",
                "Output source priority (0 Utility first, 1 Solar first, 2 SBU first)",
                "Charger source priority (0 Utility, 1 Solar, 2 Solar+Utility, 3 Solar only)",
                "Parallel max number", "Machine type (00 grid tie, 01 off grid, 10 hybrid)",
                "Topology (0 transformerless, 1 transformer)", "Output mode (00 single)",
                "Battery re-discharge voltage (V)", "PV OK condition for parallel",
                "PV power balance (0 max current, 1 max power)",
                "[not in manual] probably max charging time at C.V. stage (minutes)",
                "[not in manual] probably operation logic",
                "[not in manual] probably max discharging current"]
QDI_FIELDS = ["AC output voltage (V)", "AC output frequency (Hz)", "Max AC charging current (A)",
              "Battery under voltage (V)", "Charging float voltage (V)", "Charging bulk voltage (V)",
              "Battery re-charge voltage (V)", "Max charging current (A)", "AC input voltage range",
              "Output source priority", "Charger source priority", "Battery type", "Buzzer",
              "Power saving", "Overload restart", "Over-temperature restart", "LCD backlight",
              "Alarm on primary interrupt", "Fault code record", "Overload bypass", "LCD return to default",
              "Output mode", "Battery re-discharge voltage (V)", "PV OK condition", "PV power balance",
              "[not in manual] extra field"]


def split_reply(raw: bytes):
    """Return (payload_text, crc_ok) or (None, False) if the frame shape is wrong."""
    if len(raw) >= 4 and raw.startswith(b"(") and raw.endswith(b"\r"):
        body, crc = raw[:-3], raw[-3:-1]
        return body[1:].decode("ascii", "replace"), voltronic_crc(body) == crc
    return None, False


def numbered(names, parts):
    out = []
    for i, p in enumerate(parts):
        out.append("  %2d  %-62s %s" % (i + 1, names[i] if i < len(names) else "(unknown extra field)", p))
    return out


def decode(cmd: str, text: str):
    lines = []
    if cmd == "QPIGS":
        parts = text.split(" ")
        if len(parts) != len(QPIGS_FIELDS):
            lines.append("  note: %d fields (expected %d); showing by position" % (len(parts), len(QPIGS_FIELDS)))
        for i, p in enumerate(parts):
            name, unit = QPIGS_FIELDS[i] if i < len(QPIGS_FIELDS) else ("(unknown extra field)", "")
            lines.append("  %2d  %-58s %-9s %s" % (i + 1, name, p, unit))
        if len(parts) > 16 and len(parts[16]) == 8:
            on = [STATUS_BITS[i] for i, c in enumerate(parts[16]) if c == "1"]
            lines.append("      status bits set: %s" % (", ".join(on) or "none"))
        if len(parts) > 20 and len(parts[20]) == 3:
            on = [STATUS2_BITS[i] for i, c in enumerate(parts[20]) if c == "1"]
            lines.append("      status 2 bits set (common PI30 meaning): %s" % (", ".join(on) or "none"))
    elif cmd == "QMOD":
        lines.append("  mode: %s" % MODES.get(text, "unknown code %r" % text))
    elif cmd == "QPIWS":
        active = [QPIWS_BITS[i] + " (a%d)" % i for i, c in enumerate(text) if c == "1" and i < len(QPIWS_BITS)]
        lines.append("  %d status chars; active warnings/faults: %s" % (len(text), ", ".join(active) or "none"))
        if len(text) > 32 and "1" in text[32:]:
            lines.append("  note: characters beyond the manual's 32 are set: %s (meaning unknown)" % text[32:])
    elif cmd == "QFLAG":
        # 'E' / 'D' (uppercase) switch between the enabled and disabled lists;
        # the flag letters themselves may arrive in upper or lower case.
        state, enabled = None, {}
        for c in text:
            if c in "ED":
                state = c
            elif state:
                enabled[c.upper()] = (state == "E")
        for k, v in enabled.items():
            lines.append("  %-42s %s" % (QFLAG_NAMES.get(k, "flag " + k), "enabled" if v else "disabled"))
    elif cmd == "QPIRI":
        parts = text.split(" ")
        lines += numbered(QPIRI_FIELDS, parts)
        lines.append("  note: %d fields; 1-25 follow the manual's order, the rest are not in the manual." % len(parts))
    elif cmd == "QDI":
        lines += numbered(QDI_FIELDS, text.split(" "))
    return lines


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def log(msg=""):
    print(msg)
    with open(LOGFILE, "a") as f:
        f.write(msg + "\n")


def show(cmd, raw, secs, csv_path=None):
    log("\n> %s  (reply in %.2f s)" % (cmd, secs))
    if not raw:
        log("  no reply within the timeout")
        return False
    log("  raw : %r" % raw)
    text, ok = split_reply(raw)
    if text is None:
        log("  (not a valid reply frame: expected '(' ... CRC CR)")
        return False
    log("  CRC : %s" % ("OK" if ok else "MISMATCH, ignore this reply"))
    if not ok:
        return False
    if text in ("NAK", "ACK"):
        log("  the inverter answered %s (command not supported)" % text if text == "NAK" else "  ACK")
        return True
    log("  text: %s" % text)
    for line in decode(cmd, text):
        log(line)
    if csv_path:
        with open(csv_path, "a") as f:
            f.write("%s,%s,%s\n" % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    cmd, text.replace(",", ";")))
    return True


def find_ports():
    return sorted(glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/ttyUSB*"))


def autodetect_port():
    ports = find_ports()
    if not ports:
        sys.exit("No USB serial port found. Replug the cable and try again, or use --port.")
    return ports[0]


# ---------------------------------------------------------------------------
# Self test (no serial port needed)
# ---------------------------------------------------------------------------
def selftest():
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(("PASS  " if cond else "FAIL  ") + name)
        fails += 0 if cond else 1

    # CRC vectors produced by compiling the manual's own CRC.c
    vectors = {"QPI": "beac", "QID": "d6ea", "QVFW": "6299", "QVFW2": "c3f5", "QPIRI": "f854",
               "QFLAG": "9874", "QPIGS": "b7a9", "QMOD": "49c1", "QPIWS": "b4da", "QDI": "711b",
               "QMCHGCR": "d855", "QMUCHGCR": "2634", "QBOOT": "0b88", "QOPM": "a5c5", "QPGS0": "3fda",
               "QET": "81b6", "QLT": "3b2e", "QED20261124": "f245", "QEM202611": "60fc",
               "QEY2026": "f7ef", "QLD20261124": "d74b", "QLM202611": "39f5", "QLY2026": "bf0e"}
    for c, h in vectors.items():
        check("CRC %-8s = %s (manual CRC.c)" % (c, h), voltronic_crc(c.encode()).hex() == h)
    check("QPIGS frame bytes", build_frame("QPIGS").hex(" ") == "51 50 49 47 53 b7 a9 0d")

    # Real replies captured from the inverter on 2026-11-23
    nak = b"(NAKss\r"
    mod = b"(B\xe7\xc9\r"
    gs = (b"(000.0 00.0 230.5 49.9 0092 0061 001 446 54.60 000 100 0037 00.1 274.0 00.00 "
          b"00000 00010000 00 00 00042 010\xe4\xf3\r")
    real = {
        "QPIRI": (b"(230.0 31.3 230.0 50.0 31.3 7200 7200 48.0 47.0 46.4 57.6 57.6 8 30 010 0 0 2 9 01 0 0 54.0 "
                  b"0 1 480 0 000\x8dn\r"),
        "QDI": (b"(230.0 50.0 0030 44.0 54.0 56.4 46.0 60 0 0 2 0 0 0 0 0 1 1 1 0 1 0 54.0 0 1 224\xeb\xbc\r"),
        "QVFW": b"(VERFW:00069.07\x0e\x99\r",
        "QPIWS": b"(000001000000000000000000000000000000\xb2\xa7\r",
        "QFLAG": b"(ExyzDabjkuv\x8d\xbd\r",
    }
    for name, r in real.items():
        check("real %s reply passes CRC" % name, split_reply(r)[1])
    check("QPIRI reply has 28 fields", len(split_reply(real["QPIRI"])[0].split(" ")) == 28)
    check("QDI reply has 26 fields", len(split_reply(real["QDI"])[0].split(" ")) == 26)
    for name, r in (("NAK", nak), ("QMOD", mod), ("QPIGS", gs)):
        check("real %s reply passes CRC" % name, split_reply(r)[1])
    check("QPIGS reply has 21 fields", len(split_reply(gs)[0].split(" ")) == 21)

    # Real energy-query replies captured from the inverter on 2026-11-24
    energy_real = {
        "QET":          b"(00724100\x19\xb9\r",
        "QLT":          b"(00297000\x1a\xab\r",
        "QED20261124":  b"(00001139\xedD\r",
        "QEM202611":    b"(00182200\xac?\r",
        "QEY2026":      b"(00724100\x19\xb9\r",
        "QLD20261124":  b"(00001948\xcdS\r",
        "QLM202611":    b"(00117600d\xc6\r",
        "QLY2026":      b"(00297000\x1a\xab\r",
    }
    for name, r in energy_real.items():
        check("real %s reply passes CRC" % name, split_reply(r)[1])

    # Safety: nothing but whitelisted queries can be framed
    for bad in ["PF", "PCP00", "POP02", "PBT01", "PSDV42.0", "PCVV56.4", "PBFT54.0", "PEA", "PDA",
                "F50", "MCHGC010", "MUCHGC020", "POPM00", "PBCV48.0", "PBDV54.0", "PGR01",
                "QPIGS\rPF", "qpigs", "QPGS10", "", " QPIGS", "QPIGSX",
                "QED2026112", "QED202611245", "QEDaaaaaaaa", "QEM20261", "QEY20266",
                "QLD2026112", "QLM20261", "QLY20266", "QET ", "QETX"]:
        blocked = not is_allowed(bad)
        check("blocked %r" % bad, blocked)
    for good in (list(READ_ONLY) + ["QPGS0", "QPGS9", "QED20261124", "QEM202611", "QEY2026",
                                     "QLD20261124", "QLM202611", "QLY2026"]):
        check("allowed %s and framed with leading Q" % good, build_frame(good)[:1] == b"Q")
    check("every whitelisted command starts with Q", all(c.startswith("Q") for c in READ_ONLY))
    print("\n%s" % ("ALL TESTS PASSED" if not fails else "%d TEST(S) FAILED" % fails))
    return fails


# ---------------------------------------------------------------------------

def run_commands(port, baud, cmds, repeat=1, every=10.0, csv_path=None):
    """Open the port, run the whitelisted commands, close it. repeat=0 means until Ctrl-C."""
    for c in cmds:                       # refuse before opening the port at all
        if not is_allowed(c):
            refuse(c)
    log("=== %s  port=%s  baud=%d 8N1  (READ-ONLY) ===" % (time.strftime("%Y-%m-%d %H:%M:%S"), port, baud))
    link = ReadOnlyLink(port, baud)
    try:
        n = 0
        while repeat == 0 or n < repeat:
            for c in cmds:
                raw, secs = link.query(c)
                show(c, raw, secs, csv_path)
                time.sleep(0.5)
            n += 1
            if repeat == 0 or n < repeat:
                time.sleep(every)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        link.close()


def energy_commands_for_today():
    """QED/QEM/QEY/QLD/QLM/QLY for today's date, in UTC, plus the all-time totals."""
    now = time.gmtime()
    day = time.strftime("%Y%m%d", now)
    month = time.strftime("%Y%m", now)
    year = time.strftime("%Y", now)
    return ["QET", "QLT",
            "QED" + day, "QEM" + month, "QEY" + year,
            "QLD" + day, "QLM" + month, "QLY" + year]


def ask(prompt, default=""):
    try:
        text = input("%s%s: " % (prompt, " [%s]" % default if default != "" else ""))
    except EOFError:
        raise SystemExit
    return text.strip() or default


def pause():
    try:
        input("\nPress Enter to return to the menu...")
    except EOFError:
        raise SystemExit


def menu(port=None, baud=2400):
    """Interactive menu. Every entry runs fixed, whitelisted, read-only queries."""
    actions = {
        "1": ("Quick status (mode, live values, warnings, flags)", ["QMOD", "QPIGS", "QPIWS", "QFLAG"]),
        "2": ("Live values once (QPIGS)", ["QPIGS"]),
        "3": ("Ratings and current settings (QPIRI)", ["QPIRI"]),
        "4": ("Setting flags (QFLAG)", ["QFLAG"]),
        "5": ("Warnings and faults (QPIWS)", ["QPIWS"]),
        "6": ("Serial number and firmware (QID, QVFW, QVFW2)", ["QID", "QVFW", "QVFW2"]),
        "7": ("Default settings (QDI, read only)", ["QDI"]),
        "8": ("Energy totals: today, this month, this year, all-time", energy_commands_for_today()),
        "9": ("Every fixed read-only command in the manual", list(READ_ONLY) + ["QPGS0"]),
    }
    while True:
        ports = find_ports()
        shown = port or (ports[0] if ports else "NOT FOUND (replug the cable)")
        print("\n==== Xunzel IXS-ON 7200: READ-ONLY tool ====")
        print("Port: %s   Baud: %d   (nothing here can change the inverter)\n" % (shown, baud))
        for k, (label, _) in actions.items():
            print("  %s  %s" % (k, label))
        print(" 10  Watch live values repeatedly (Ctrl-C to stop)")
        print(" 11  Log live values to a CSV file (Ctrl-C to stop)")
        print(" 12  Self-test (CRC + safety checks, no inverter needed)")
        print(" 13  List the allowed commands")
        print("  p  Choose serial port / baud rate")
        print("  0  Quit")
        choice = ask("\nChoose").lower()
        try:
            if choice == "0" or choice == "q":
                return
            elif choice in actions:
                use = port or (ports[0] if ports else None)
                if not use:
                    print("No USB serial port found. Replug the cable, or pick one with p.")
                else:
                    run_commands(use, baud, actions[choice][1])
            elif choice in ("10", "11"):
                use = port or (ports[0] if ports else None)
                if not use:
                    print("No USB serial port found. Replug the cable, or pick one with p.")
                else:
                    every = float(ask("Seconds between readings", "10" if choice == "10" else "30"))
                    csv_path = None
                    if choice == "11":
                        csv_path = ask("CSV file name", "xunzel_log.csv")
                    print("Running. Press Ctrl-C to stop.")
                    run_commands(use, baud, ["QPIGS"], repeat=0, every=every, csv_path=csv_path)
            elif choice == "12":
                selftest()
            elif choice == "13":
                for k, v in READ_ONLY.items():
                    print("%-9s %-34s %s" % (k, build_frame(k).hex(" "), v))
                print("%-9s %-34s %s" % ("QPGS0-9", "", "Parallel info for unit n (may be NAK)"))
                print()
                print("Energy totals (date is an argument you supply, not a fixed command):")
                print("%-14s %-8s %s" % ("QET", "fixed", "Total PV energy generated, all-time (Wh)"))
                print("%-14s %-8s %s" % ("QLT", "fixed", "Total load (output) energy, all-time (Wh)"))
                print("%-14s %-8s %s" % ("QED<YYYYMMDD>", "e.g.", "QED20261124 - PV energy for one day (Wh)"))
                print("%-14s %-8s %s" % ("QEM<YYYYMM>", "e.g.", "QEM202611   - PV energy for one month (Wh)"))
                print("%-14s %-8s %s" % ("QEY<YYYY>", "e.g.", "QEY2026     - PV energy for one year (Wh)"))
                print("%-14s %-8s %s" % ("QLD<YYYYMMDD>", "e.g.", "QLD20261124 - load energy for one day (Wh)"))
                print("%-14s %-8s %s" % ("QLM<YYYYMM>", "e.g.", "QLM202611   - load energy for one month (Wh)"))
                print("%-14s %-8s %s" % ("QLY<YYYY>", "e.g.", "QLY2026     - load energy for one year (Wh)"))
            elif choice == "p":
                for n, pth in enumerate(ports, 1):
                    print("  %d  %s" % (n, pth))
                sel = ask("Port number or full path (Enter = auto)", "")
                if sel.isdigit() and 1 <= int(sel) <= len(ports):
                    port = ports[int(sel) - 1]
                elif sel:
                    port = sel
                else:
                    port = None
                baud = int(ask("Baud rate", str(baud)))
            else:
                print("Please choose one of the numbers shown.")
                continue
        except OSError as e:
            print("Could not use the serial port: %s" % e)
        except ValueError:
            print("That was not a number.")
        pause()


def main():
    args = sys.argv[1:]
    port, baud, csv_path, repeat, every, cmds, want_menu = None, 2400, None, 1, 10.0, [], False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--port":
            port = args[i + 1]; i += 1
        elif a == "--baud":
            baud = int(args[i + 1]); i += 1
        elif a == "--csv":
            csv_path = args[i + 1]; i += 1
        elif a == "--repeat":
            repeat = int(args[i + 1]); i += 1
        elif a == "--every":
            every = float(args[i + 1]); i += 1
        elif a == "--menu":
            want_menu = True
        elif a == "--list":
            for k, v in READ_ONLY.items():
                print("%-9s %-34s %s" % (k, build_frame(k).hex(" "), v))
            print("%-9s %-34s %s" % ("QPGS0-9", "", "Parallel info for unit n (may be NAK)"))
            print()
            print("Energy totals (date is an argument you supply, not a fixed command):")
            print("%-14s %-8s %s" % ("QET", "fixed", "Total PV energy generated, all-time (Wh)"))
            print("%-14s %-8s %s" % ("QLT", "fixed", "Total load (output) energy, all-time (Wh)"))
            print("%-14s %-8s %s" % ("QED<YYYYMMDD>", "e.g.", "QED20261124 - PV energy for one day (Wh)"))
            print("%-14s %-8s %s" % ("QEM<YYYYMM>", "e.g.", "QEM202611   - PV energy for one month (Wh)"))
            print("%-14s %-8s %s" % ("QEY<YYYY>", "e.g.", "QEY2026     - PV energy for one year (Wh)"))
            print("%-14s %-8s %s" % ("QLD<YYYYMMDD>", "e.g.", "QLD20261124 - load energy for one day (Wh)"))
            print("%-14s %-8s %s" % ("QLM<YYYYMM>", "e.g.", "QLM202611   - load energy for one month (Wh)"))
            print("%-14s %-8s %s" % ("QLY<YYYY>", "e.g.", "QLY2026     - load energy for one year (Wh)"))
            return
        elif a == "--selftest":
            sys.exit(1 if selftest() else 0)
        elif a in ("-h", "--help"):
            print(__doc__); return
        elif a == "--version":
            print(__version__); return
        elif a == "all":
            cmds += list(READ_ONLY) + ["QPGS0"] + energy_commands_for_today()
        else:
            cmds.append(a)
        i += 1

    if want_menu or not args:
        try:
            menu(port, baud)
        except KeyboardInterrupt:
            print()
        return

    cmds = cmds or DEFAULT_SET
    for c in cmds:
        if not is_allowed(c):
            refuse(c)
    run_commands(port or autodetect_port(), baud, cmds, repeat, every, csv_path)


if __name__ == "__main__":
    main()
