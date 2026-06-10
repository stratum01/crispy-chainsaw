# CIVOPS Recon Radar — Design Spec

**Date:** 2026-06-10
**Status:** Approved

## Overview

A mobile-first wireless reconnaissance tool for Android (Termux), built for two primary use cases:

1. **Security research / auditing** — live analysis of WiFi and Bluetooth environments in authorized test scenarios
2. **Field data collection** — persistent logging and mapping of wireless signals over time (wardriving, coverage mapping, anomaly detection)

The architecture is designed for a clean Linux desktop port: swapping one backend module gives full functionality on a Linux laptop with no changes to the UI, storage, or export layers.

---

## Architecture

Five layers, each with one job:

```
civops/
├── civops.py               # entry point — detects backend, launches Textual app
├── requirements.txt        # textual; all other deps are stdlib
├── backends/
│   ├── base.py             # abstract interface: scan_wifi, scan_bluetooth, get_location
│   ├── termux.py           # Termux API backend (Android) — shells out to termux-api CLI
│   └── linux.py            # Linux backend skeleton — raises NotImplementedError, ready to implement
├── scanners/
│   ├── wifi.py             # calls backend, normalizes to WiFiNetwork, diffs for events
│   ├── bluetooth.py        # calls backend, normalizes to BTDevice, diffs for events
│   └── gps.py              # polls backend for GPSLocation on independent 3s timer
├── storage/
│   ├── database.py         # SQLite (WAL mode): sessions, wifi_detections, bt_detections, gps_track
│   └── logger.py           # JSONL append log, one event per line
├── ui/
│   ├── app.py              # Textual App — tab routing, hotkey dispatch
│   ├── radar.py            # Radar screen — live WiFi + BT tables, signal bars, OUI vendor
│   ├── log_view.py         # Log screen — scrolling event stream, search/filter
│   └── map_view.py         # Map screen — ASCII GPS track, session summary, export triggers
├── export/
│   ├── kml.py              # KML export — placemarks per detection, Google Maps compatible
│   └── gpx.py              # GPX export — waypoints + track, QGIS compatible
└── data/
    └── oui.txt             # bundled IEEE OUI database (~5MB) for vendor lookup
```

### Data flow

```
Termux Backend (termux-wifi-scaninfo / termux-bluetooth-scan / termux-location)
    ↓
Scanners (normalize raw JSON → dataclasses, diff for appear/disappear events)
    ↓
Storage (SQLite + JSONL — every detection written to both)
    ↓
Textual UI (Radar / Log / Map — reactive updates via Textual message system)
```

---

## Data Models

```python
@dataclass
class WiFiNetwork:
    ssid: str
    bssid: str
    rssi: int
    frequency: int        # MHz
    capabilities: str     # e.g. WPA3, WPA2, OPEN
    lat: float | None
    lon: float | None
    timestamp: datetime

@dataclass
class BTDevice:
    name: str
    address: str
    rssi: int
    device_type: str      # Classic | BLE
    manufacturer: str | None   # OUI lookup result
    lat: float | None
    lon: float | None
    timestamp: datetime

@dataclass
class GPSLocation:
    lat: float
    lon: float
    altitude: float
    accuracy: float       # meters
    timestamp: datetime
```

---

## Backend Interface

`backends/base.py` defines the abstract contract both backends must satisfy:

```python
class BaseBackend(ABC):
    def scan_wifi(self) -> list[WiFiNetwork]: ...
    def scan_bluetooth(self) -> list[BTDevice]: ...
    def get_location(self) -> GPSLocation | None: ...
```

**Termux backend** (`termux.py`): shells out to `termux-wifi-scaninfo`, `termux-bluetooth-scan`, `termux-location -p gps` via subprocess, parses JSON output.

**Linux backend** (`linux.py`): stub that raises `NotImplementedError` on each method. Intended to be implemented using `iw`, `hcitool`/`bluetoothctl`, and `gpsd`.

Backend is auto-detected at startup: if `termux-wifi-scaninfo` is on PATH, use Termux backend; otherwise use Linux backend. Overridable via `--backend termux|linux` flag.

---

## UI — Three Modes

### Radar (default)

- Auto-refreshes every 5 seconds (configurable via `--interval`)
- WiFi and BT each in separate tables
- Signal strength shown as `▓` bar (9 chars) + dBm value, color-coded:
  - Green: ≥ -65 dBm
  - Orange: -65 to -80 dBm
  - Red: < -80 dBm
- Vendor column populated from OUI lookup (bundled `oui.txt`, cached in memory per session)
- Open networks flagged with `⚠`
- Status bar: session duration, current GPS coordinates and accuracy

### Log

- Scrolling event stream, auto-scrolls to bottom
- Event types: `[+WIFI]` appeared, `[-WIFI]` disappeared, `[RSSI]` significant change (>10 dBm delta), `[GPS]` location fix, `[+BT]`, `[-BT]`, `[+BLE]`, `[-BLE]`
- All events timestamped (HH:MM:SS)
- `f` hotkey: filter by type (WiFi / BT / GPS / all)
- `/` hotkey: search by SSID or address
- Footer shows current JSONL log filename

### Map

- Left panel: ASCII GPS track rendered from accumulated `gps_track` rows
  - `.` for path points, `★` for session start, `W` for WiFi detection site, `B` for BT detection site
  - Coordinate range auto-scaled to terminal width/height
- Right panel: session summary (duration, distance estimate, counts, open network warnings)
- `k` hotkey: export KML to `~/civops-data/<session>/civops.kml`
- `g` hotkey: export GPX to `~/civops-data/<session>/civops.gpx`

---

## Storage

### SQLite schema

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    started_at TEXT,
    ended_at TEXT,
    wifi_count INTEGER,
    bt_count INTEGER,
    kml_path TEXT,
    gpx_path TEXT
);

CREATE TABLE wifi_detections (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    ssid TEXT, bssid TEXT, rssi INTEGER,
    frequency INTEGER, capabilities TEXT,
    lat REAL, lon REAL, timestamp TEXT
);

CREATE TABLE bt_detections (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    name TEXT, address TEXT, rssi INTEGER,
    device_type TEXT, manufacturer TEXT,
    lat REAL, lon REAL, timestamp TEXT
);

CREATE TABLE gps_track (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    lat REAL, lon REAL, altitude REAL,
    accuracy REAL, timestamp TEXT
);
```

SQLite uses WAL mode to survive interruptions (incoming calls, app backgrounded).

### JSONL log

One JSON object per line, appended to `~/civops-data/civops-YYYY-MM-DD-HH-MM.jsonl`:

```json
{"type": "wifi", "ssid": "HOME-NET", "bssid": "bc:ae:c5:12:34:56", "rssi": -52, "frequency": 2437, "capabilities": "WPA3", "lat": 37.7749, "lon": -122.4194, "timestamp": "2026-06-10T14:31:55"}
{"type": "bt", "name": "AirPods Pro", "address": "40:4d:7f:11:22:33", "rssi": -55, "device_type": "Classic", "manufacturer": "Apple", "lat": 37.7749, "lon": -122.4194, "timestamp": "2026-06-10T14:31:57"}
```

---

## GPS

- Polled every 3 seconds via `termux-location -p gps`, on an independent timer from WiFi/BT scans
- Every detection record gets stamped with the most recent valid GPS fix (`lat`, `lon`)
- If no fix yet: `lat=None`, `lon=None` — detection still logged, Map view shows "waiting for GPS fix"
- GPS failure is non-fatal; scanning continues without coordinates

---

## OUI Vendor Lookup

- Bundled as `data/oui.txt` (~5MB, IEEE public registry)
- Looked up on first detection per address prefix (first 3 octets)
- Result cached in a dict for the session duration — no repeated file lookups, no network calls

---

## Export

**KML** (`export/kml.py`):
- One `<Placemark>` per unique WiFi network (by BSSID), positioned at first-detection coordinates
- Placemark name: SSID. Description: BSSID, RSSI, capabilities, timestamp
- Open networks get a distinct icon/style
- GPS track exported as a `<LineString>`

**GPX** (`export/gpx.py`):
- `<wpt>` per unique WiFi/BT detection, positioned at first-detection coordinates
- `<trk>` for the full GPS path

Both export to `~/civops-data/<session-timestamp>/` and print the path to the Log view on completion.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `termux-api` not installed | Startup error with install instructions (`pkg install termux-api`) |
| Location/Bluetooth permission denied | Startup error with permission grant instructions |
| GPS unavailable | Non-fatal — detections continue with `lat=None`, Map shows "waiting for GPS fix" |
| Bluetooth scanner fails mid-session | Warning in Log view, WiFi scanning continues |
| JSONL write fails | Logs to stderr, session continues (SQLite is primary) |
| SQLite interrupted | WAL mode ensures no corruption |

---

## Testing

- **Unit tests** for scanners: inject `MockBackend` returning fixture JSON, assert normalized dataclass output
- **Unit tests** for storage: in-memory SQLite (`:memory:`), assert correct rows written
- **Unit tests** for export: assert KML/GPX output is well-formed XML with expected placemarks
- **No Textual UI tests** in v1 — logic lives in backend/scanner/storage/export layers
- `MockBackend` implements `BaseBackend` with hardcoded fixture data — no real device needed to run tests

---

## Scanning Behavior

- WiFi and BT scanned together on one timer (default 5s, `--interval N` to override)
- Each scan result diffed against previous to emit `appeared` / `disappeared` events
- Significant RSSI change (>10 dBm delta on a known device) emits a `[RSSI]` log event
- GPS runs on its own 3s timer — a slow fix never blocks a WiFi/BT scan cycle

---

## Linux Port Roadmap

To port to Linux desktop, implement `backends/linux.py`:

| Termux API | Linux equivalent |
|---|---|
| `termux-wifi-scaninfo` | `iw dev <iface> scan` |
| `termux-bluetooth-scan` | `hcitool scan` + `hcitool lescan` (or `bluetoothctl`) |
| `termux-location -p gps` | `gpsd` + `gpspipe -w` |

No other files need to change.

---

## Dependencies

```
textual>=0.50
# stdlib only beyond that: sqlite3, subprocess, json, dataclasses, pathlib, datetime
```

Install on Termux:
```bash
pkg install python termux-api
pip install textual
```
