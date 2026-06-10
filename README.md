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
- Three TUI modes: Radar (live tables), Log (event stream with filter/search), Map (ASCII GPS track)
- Export to KML (Google Maps) and GPX (QGIS)
- SQLite storage in WAL mode — survives incoming calls and app backgrounding
- JSONL append log for easy post-processing

---

## Requirements

- Android phone with [Termux](https://f-droid.org/packages/com.termux/) and [Termux:API](https://f-droid.org/packages/com.termux.api/) installed from **F-Droid**
- Python 3.11+
- `textual` Python package

> **Note:** Install Termux from F-Droid, not the Play Store. The Play Store version is outdated and no longer maintained.

---

## Installation

### Option A: Clone from GitHub

The simplest method if you have a GitHub account.

**On your computer — push the repo:**
```bash
cd /home/stratum/civops
git remote add origin https://github.com/YOUR_USERNAME/civops.git
git push -u origin HEAD
```

**On your phone in Termux:**
```bash
pkg update && pkg install python git termux-api
pip install textual
git clone https://github.com/YOUR_USERNAME/civops.git
cd civops
python civops.py
```

---

### Option B: Transfer over WiFi (no GitHub needed)

Both devices must be on the same network.

**On your computer — serve the project:**
```bash
ip addr | grep "inet " | grep -v 127    # note your IP, e.g. 192.168.1.42
cd /home/stratum
python3 -m http.server 8000
```

**On your phone in Termux:**
```bash
pkg update && pkg install python wget termux-api
pip install textual
wget -r -np -nH --cut-dirs=1 http://192.168.1.42:8000/civops/
cd civops
python civops.py
```

---

### Option C: USB with ADB

Enable **USB debugging** on your phone first (Settings → Developer Options).

**On your computer:**
```bash
cd /home/stratum
tar czf civops.tar.gz civops/ --exclude='civops/venv' --exclude='civops/__pycache__'
adb push civops.tar.gz /data/data/com.termux/files/home/
```

**On your phone in Termux:**
```bash
tar xzf civops.tar.gz
pkg update && pkg install python termux-api
pip install textual
cd civops
python civops.py
```

---

### First-run setup (all methods)

After installing, run this once to grant Termux storage access:
```bash
termux-setup-storage
```

On first scan, Android will prompt for **Location** and **Bluetooth** permissions — grant both. Precise location is required for WiFi scanning on Android 10+.

---

## Usage

```bash
python civops.py                     # auto-detect backend, 5s scan interval
python civops.py --interval 10       # scan every 10 seconds
python civops.py --backend linux     # force Linux backend (desktop)
python civops.py --db ~/my.db        # custom database path
```

Session data is written to `~/civops-data/`:
- `civops.db` — SQLite database
- `civops-YYYY-MM-DD-HH-MM.jsonl` — JSONL event log

---

## TUI Modes

Switch between modes with `r` / `l` / `m`. Press `q` to quit.

### Radar
Live WiFi and Bluetooth tables, updated every scan cycle.

- Signal strength shown as `▓` bar (9 chars) + dBm value
- Color coding: green ≥ -65 dBm, yellow ≥ -80, red < -80
- Open networks flagged with `⚠`
- Vendor column populated from bundled OUI database

### Log
Scrolling event stream of everything that happened this session.

- `f` — cycle filter: all / wifi / bt / gps
- `/` — search by SSID or address
- `Esc` — clear search

Event types: `[+WIFI]` `[-WIFI]` `[RSSI]` `[+BT]` `[-BT]` `[+BLE]` `[-BLE]` `[GPS]` `[EXPORT]`

### Map
ASCII rendering of your GPS track with detection sites overlaid.

```
  · path  ★ start  W wifi  B bt
```

- `k` — export KML to `~/civops-data/civops-TIMESTAMP.kml`
- `g` — export GPX to `~/civops-data/civops-TIMESTAMP.gpx`

---

## Export Formats

| Format | Open with | Contents |
|--------|-----------|----------|
| KML | Google Maps, Google Earth | WiFi/BT placemarks, GPS track as LineString |
| GPX | QGIS, OsmAnd, Garmin | WiFi/BT waypoints, GPS track with elevation |

Detections without GPS coordinates are excluded from exports.

---

## Linux Port

The backend is the only platform-specific layer. To port to Linux desktop, implement `backends/linux.py`:

| Termux API | Linux equivalent |
|---|---|
| `termux-wifi-scaninfo` | `iw dev <iface> scan` |
| `termux-bluetooth-scan` | `hcitool scan` + `bluetoothctl` |
| `termux-location -p gps` | `gpsd` + `gpspipe -w` |

No other files need to change. Run with `--backend linux` once implemented.

---

## Architecture

```
backends/    platform I/O (Termux API subprocess calls)
scanners/    normalize raw JSON → dataclasses, diff for events
storage/     SQLite (WAL) + JSONL append log
export/      KML and GPX generation
ui/          Textual TUI — Radar / Log / Map screens
```

---

## Legal

Only use on networks and devices you own or have explicit written permission to scan. Unauthorized network scanning may violate local laws.
