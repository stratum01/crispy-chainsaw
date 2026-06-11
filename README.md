# CIVOPS Recon Radar

A mobile WiFi and Bluetooth reconnaissance tool for Android (Termux). Scans your wireless environment in real time, logs every detection with GPS coordinates, and exports your session data as KML (Google Maps) or GPX (QGIS).

Built for two use cases:
- **Security research / auditing** — live analysis of wireless environments in authorized test scenarios
- **Field data collection** — wardriving, coverage mapping, signal anomaly detection

---

## Features

- Live WiFi and Bluetooth scanning with signal strength bars and color coding
- GPS coordinates attached to every detection
- OUI vendor lookup (bundled IEEE database — no network calls)
- Web UI served from Termux, viewable in any browser on the same device
- Export to KML (Google Maps) and GPX (QGIS)
- SQLite storage in WAL mode — survives incoming calls and app backgrounding
- JSONL append log for easy post-processing

---

## Requirements

- Android phone with [Termux](https://f-droid.org/packages/com.termux/) and [Termux:API](https://f-droid.org/packages/com.termux.api/) installed from **F-Droid**
- Python 3.11+
- `flask` and `textual` Python packages

> **Note:** Install Termux from F-Droid, not the Play Store. The Play Store version is outdated and no longer maintained.

---

## Installation

### Option A: Clone from GitHub

**On your phone in Termux:**
```bash
pkg update && pkg upgrade
pkg install python git termux-api openssh
pip install flask textual
git clone https://github.com/stratum01/crispy-chainsaw.git
cd crispy-chainsaw
termux-setup-storage
python civops.py --web
```

---

### Option B: Transfer over WiFi (no GitHub needed)

Both devices must be on the same network.

**On your computer:**
```bash
ip addr | grep "inet " | grep -v 127    # note your IP, e.g. 192.168.1.42
cd ~
python3 -m http.server 8000
```

**On your phone in Termux:**
```bash
pkg update && pkg install python wget termux-api
pip install flask textual
wget -r -np -nH --cut-dirs=1 http://192.168.1.42:8000/crispy-chainsaw/
cd crispy-chainsaw
python civops.py --web
```

---

### Option C: USB with ADB

Enable **USB debugging** on your phone first (Settings → Developer Options).

**On your computer:**
```bash
tar czf civops.tar.gz crispy-chainsaw/ --exclude='__pycache__'
adb push civops.tar.gz /data/data/com.termux/files/home/
```

**On your phone in Termux:**
```bash
tar xzf civops.tar.gz
pkg update && pkg install python termux-api
pip install flask textual
cd crispy-chainsaw
python civops.py --web
```

---

### First-run setup (all methods)

Run this once to grant Termux storage access:
```bash
termux-setup-storage
```

Run these once to trigger Android permission prompts:
```bash
termux-wifi-scaninfo       # grants Location permission
termux-location -p gps     # grants precise GPS access
```

---

## Usage

```bash
# Web UI — recommended (open http://localhost:8080 in Chrome)
python civops.py --web
python civops.py --web --port 9090    # custom port

# Terminal UI (experimental)
python civops.py

# Options for both modes
python civops.py --web --interval 10  # scan every 10 seconds
python civops.py --web --db ~/my.db   # custom database path
python civops.py --web --backend linux
```

Session data is written to `~/civops-data/`:
- `civops.db` — SQLite database
- `civops-YYYY-MM-DD-HH-MM.jsonl` — JSONL event log

---

## Web UI

Start the server, then open **http://localhost:8080** in Chrome on your phone.

The page refreshes every 5 seconds and shows:
- WiFi networks sorted by signal strength with `▓` signal bars
- Color coding: green ≥ -65 dBm, orange ≥ -80, red < -80
- GPS fix with accuracy
- Live event log (appeared / disappeared / RSSI changes)

To run in the background while using your phone for other things:

```bash
nohup python civops.py --web > ~/civops-data/server.log 2>&1 &
echo $!   # note the PID to kill it later
```

Stop it with `kill <PID>` or `pkill -f civops.py`.

---

## Export Formats

| Format | Open with | Contents |
|--------|-----------|----------|
| KML | Google Maps, Google Earth | WiFi/BT placemarks, GPS track as LineString |
| GPX | QGIS, OsmAnd, Garmin | WiFi/BT waypoints, GPS track with elevation |

Exports are triggered via the TUI Map screen (`k` for KML, `g` for GPX) and saved to `~/civops-data/`.

---

## Linux Port

The backend is the only platform-specific layer. To port to Linux desktop, implement `backends/linux.py`:

| Termux API | Linux equivalent |
|---|---|
| `termux-wifi-scaninfo` | `sudo iw dev <iface> scan` or `nmcli dev wifi list` |
| `termux-bluetooth-scan` | `bluetoothctl scan on` or `hcitool lescan` |
| `termux-location -p gps` | `gpsd` + `gpspipe -w` (or omit for fixed location) |

No other files need to change. Run with `--backend linux` once implemented.

---

## Architecture

```
backends/    platform I/O (Termux API subprocess calls)
scanners/    normalize raw JSON → dataclasses, diff for events
storage/     SQLite (WAL) + JSONL append log
export/      KML and GPX generation
ui/          web.py (Flask — primary), app.py (Textual TUI)
```

---

## Legal

Only use on networks and devices you own or have explicit written permission to scan. Unauthorized network scanning may violate local laws.
