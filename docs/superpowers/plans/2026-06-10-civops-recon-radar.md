# CIVOPS Recon Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Termux/Android WiFi+Bluetooth recon tool with a multi-mode Textual TUI (Radar/Log/Map), GPS-tagged detections, SQLite+JSONL storage, and KML/GPX export.

**Architecture:** Five layers — backends (Termux API subprocess calls), scanners (normalize + diff), storage (SQLite + JSONL), UI (Textual TUI), export (KML/GPX). The backend interface is the only platform-specific code; swapping `termux.py` for `linux.py` ports the entire app to desktop with no other changes.

**Tech Stack:** Python 3.11+, textual>=0.50, pytest>=7.0, sqlite3 (stdlib), subprocess (stdlib), xml.etree.ElementTree (stdlib)

---

## File Map

```
civops/
├── civops.py                  # entry point — arg parsing, backend detection, app launch
├── models.py                  # shared dataclasses: WiFiNetwork, BTDevice, GPSLocation
├── oui.py                     # IEEE OUI vendor lookup, in-memory cache
├── requirements.txt
├── backends/
│   ├── __init__.py
│   ├── base.py                # BaseBackend ABC
│   ├── termux.py              # shells out to termux-wifi-scaninfo / termux-bluetooth-scan / termux-location
│   └── linux.py               # NotImplementedError stubs — desktop port skeleton
├── scanners/
│   ├── __init__.py
│   ├── wifi.py                # WiFiScanner: normalize + appeared/disappeared/updated diff
│   ├── bluetooth.py           # BTScanner: normalize + appeared/disappeared diff + OUI lookup
│   └── gps.py                 # GPSScanner: poll backend, cache last known fix
├── storage/
│   ├── __init__.py
│   ├── database.py            # SQLite (WAL): sessions, wifi_detections, bt_detections, gps_track
│   └── logger.py              # JSONL append: one event per line
├── ui/
│   ├── __init__.py
│   ├── app.py                 # CivopsApp: tabs, hotkeys, add_log_event()
│   ├── radar.py               # RadarScreen: live WiFi+BT tables, signal bars, scan timer
│   ├── log_view.py            # LogScreen: scrolling event stream, add_event()
│   └── map_view.py            # MapScreen: ASCII GPS track, session summary, KML/GPX export
├── export/
│   ├── __init__.py
│   ├── kml.py                 # export_kml(): KML placemarks + LineString track
│   └── gpx.py                 # export_gpx(): GPX waypoints + trk
├── data/
│   └── oui.txt                # bundled IEEE OUI database (~5MB)
└── tests/
    ├── __init__.py
    ├── conftest.py             # make_wifi(), make_bt(), make_gps() factory functions
    ├── test_oui.py
    ├── test_backends.py
    ├── test_wifi_scanner.py
    ├── test_bt_scanner.py
    ├── test_gps_scanner.py
    ├── test_database.py
    ├── test_logger.py
    ├── test_kml.py
    └── test_gpx.py
```

---

## Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `backends/__init__.py`, `scanners/__init__.py`, `storage/__init__.py`, `ui/__init__.py`, `export/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
textual>=0.50
pytest>=7.0
```

- [ ] **Step 2: Create directories and empty __init__.py files**

```bash
mkdir -p backends scanners storage ui export data tests
touch backends/__init__.py scanners/__init__.py storage/__init__.py ui/__init__.py export/__init__.py tests/__init__.py
```

- [ ] **Step 3: Create tests/conftest.py**

```python
# tests/conftest.py
from datetime import datetime
from models import WiFiNetwork, BTDevice, GPSLocation


def make_wifi(**kwargs):
    defaults = dict(
        ssid="TEST-NET", bssid="aa:bb:cc:dd:ee:ff", rssi=-60,
        frequency=2437, capabilities="WPA2",
        lat=37.7749, lon=-122.4194, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return WiFiNetwork(**{**defaults, **kwargs})


def make_bt(**kwargs):
    defaults = dict(
        name="TestDevice", address="11:22:33:44:55:66", rssi=-65,
        device_type="Classic", manufacturer="Apple",
        lat=37.7749, lon=-122.4194, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return BTDevice(**{**defaults, **kwargs})


def make_gps(**kwargs):
    defaults = dict(
        lat=37.7749, lon=-122.4194, altitude=12.0,
        accuracy=8.0, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return GPSLocation(**{**defaults, **kwargs})
```

- [ ] **Step 4: Install dependencies**

```bash
pip install textual pytest
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt backends/__init__.py scanners/__init__.py storage/__init__.py ui/__init__.py export/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Shared data models

**Files:**
- Create: `models.py`

- [ ] **Step 1: Create models.py**

```python
# models.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WiFiNetwork:
    ssid: str
    bssid: str
    rssi: int
    frequency: int
    capabilities: str
    lat: float | None
    lon: float | None
    timestamp: datetime


@dataclass
class BTDevice:
    name: str
    address: str
    rssi: int
    device_type: str    # "Classic" | "BLE"
    manufacturer: str | None
    lat: float | None
    lon: float | None
    timestamp: datetime


@dataclass
class GPSLocation:
    lat: float
    lon: float
    altitude: float
    accuracy: float
    timestamp: datetime
```

- [ ] **Step 2: Verify models are importable**

```bash
python -c "from models import WiFiNetwork, BTDevice, GPSLocation; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add models.py
git commit -m "feat: add shared data models"
```

---

## Task 3: OUI vendor lookup

**Files:**
- Create: `oui.py`
- Download: `data/oui.txt`
- Create: `tests/test_oui.py`

The IEEE OUI file format has lines like:
`00-00-0C   (hex)		Cisco Systems, Inc`
We only parse `(hex)` lines.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_oui.py
from oui import lookup_vendor


def test_lookup_known_vendor(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text(
        "00-00-0C   (hex)\t\tCisco Systems, Inc\n"
        "00-50-56   (hex)\t\tVMware, Inc.\n"
    )
    assert lookup_vendor("00:00:0c:11:22:33", str(oui_file)) == "Cisco Systems, Inc"


def test_lookup_case_insensitive(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text("00-50-56   (hex)\t\tVMware, Inc.\n")
    assert lookup_vendor("00:50:56:aa:bb:cc", str(oui_file)) == "VMware, Inc."


def test_lookup_unknown_returns_none(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text("00-00-0C   (hex)\t\tCisco Systems, Inc\n")
    assert lookup_vendor("ff:ff:ff:11:22:33", str(oui_file)) is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_oui.py -v
```
Expected: `ImportError: No module named 'oui'`

- [ ] **Step 3: Download oui.txt**

```bash
curl -o data/oui.txt https://standards-oui.ieee.org/oui/oui.txt
```
(~5MB — only needed once)

- [ ] **Step 4: Implement oui.py**

```python
# oui.py
from pathlib import Path

_DEFAULT_OUI_PATH = Path(__file__).parent / "data" / "oui.txt"
_cache: dict[str, str | None] = {}


def lookup_vendor(mac: str, oui_path: str | None = None) -> str | None:
    path = oui_path or str(_DEFAULT_OUI_PATH)
    prefix = mac.upper().replace(":", "-")[:8]
    if prefix in _cache:
        return _cache[prefix]
    vendor = _parse_oui_file(path, prefix)
    _cache[prefix] = vendor
    return vendor


def _parse_oui_file(path: str, prefix: str) -> str | None:
    try:
        with open(path) as f:
            for line in f:
                if "(hex)" in line and line.upper().startswith(prefix):
                    return line.split("\t\t", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_oui.py -v
```
Expected: all 3 PASS

- [ ] **Step 6: Commit**

```bash
git add oui.py data/oui.txt tests/test_oui.py
git commit -m "feat: add OUI vendor lookup with bundled IEEE database"
```

---

## Task 4: Backend base + Termux backend

**Files:**
- Create: `backends/base.py`
- Create: `backends/termux.py`
- Create: `tests/test_backends.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_backends.py
import json
from unittest.mock import patch
from backends.termux import TermuxBackend
from models import WiFiNetwork, BTDevice, GPSLocation

WIFI_JSON = json.dumps([{
    "ssid": "HOME-NET", "bssid": "bc:ae:c5:12:34:56",
    "rssi": -52, "frequency": 2437, "capabilities": "[WPA2-PSK-CCMP][ESS]"
}])
BT_JSON = json.dumps([{
    "name": "AirPods Pro", "address": "40:4D:7F:11:22:33",
    "rssi": -55, "type": 1
}])
GPS_JSON = json.dumps({
    "latitude": 37.7749, "longitude": -122.4194,
    "altitude": 12.0, "accuracy": 8.0
})


def test_termux_scan_wifi_returns_wifi_networks():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = WIFI_JSON
        mock_run.return_value.returncode = 0
        results = TermuxBackend().scan_wifi()
    assert len(results) == 1
    assert isinstance(results[0], WiFiNetwork)
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "bc:ae:c5:12:34:56"
    assert results[0].rssi == -52


def test_termux_scan_bluetooth_returns_bt_devices():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = BT_JSON
        mock_run.return_value.returncode = 0
        results = TermuxBackend().scan_bluetooth()
    assert len(results) == 1
    assert isinstance(results[0], BTDevice)
    assert results[0].name == "AirPods Pro"
    assert results[0].device_type == "Classic"


def test_termux_get_location_returns_gps_location():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = GPS_JSON
        mock_run.return_value.returncode = 0
        loc = TermuxBackend().get_location()
    assert isinstance(loc, GPSLocation)
    assert loc.lat == 37.7749
    assert loc.lon == -122.4194


def test_termux_get_location_returns_none_on_failure():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        loc = TermuxBackend().get_location()
    assert loc is None


def test_termux_scan_wifi_returns_empty_on_failure():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        results = TermuxBackend().scan_wifi()
    assert results == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_backends.py -v
```
Expected: `ImportError: No module named 'backends.termux'`

- [ ] **Step 3: Implement backends/base.py**

```python
# backends/base.py
from abc import ABC, abstractmethod
from models import WiFiNetwork, BTDevice, GPSLocation


class BaseBackend(ABC):
    @abstractmethod
    def scan_wifi(self) -> list[WiFiNetwork]: ...

    @abstractmethod
    def scan_bluetooth(self) -> list[BTDevice]: ...

    @abstractmethod
    def get_location(self) -> GPSLocation | None: ...
```

- [ ] **Step 4: Implement backends/termux.py**

```python
# backends/termux.py
import json
import subprocess
from datetime import datetime
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation

_BT_TYPE_MAP = {1: "Classic", 2: "BLE", 3: "BLE"}


class TermuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        result = subprocess.run(
            ["termux-wifi-scaninfo"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return []
        networks = []
        for item in json.loads(result.stdout):
            networks.append(WiFiNetwork(
                ssid=item.get("ssid", ""),
                bssid=item.get("bssid", ""),
                rssi=item.get("rssi", 0),
                frequency=item.get("frequency", 0),
                capabilities=item.get("capabilities", ""),
                lat=None,
                lon=None,
                timestamp=datetime.now(),
            ))
        return networks

    def scan_bluetooth(self) -> list[BTDevice]:
        result = subprocess.run(
            ["termux-bluetooth-scan", "-d", "4"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return []
        devices = []
        for item in json.loads(result.stdout):
            devices.append(BTDevice(
                name=item.get("name") or item.get("address", ""),
                address=item.get("address", ""),
                rssi=item.get("rssi", 0),
                device_type=_BT_TYPE_MAP.get(item.get("type", 1), "Classic"),
                manufacturer=None,
                lat=None,
                lon=None,
                timestamp=datetime.now(),
            ))
        return devices

    def get_location(self) -> GPSLocation | None:
        result = subprocess.run(
            ["termux-location", "-p", "gps"], capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            data = json.loads(result.stdout)
            return GPSLocation(
                lat=data["latitude"],
                lon=data["longitude"],
                altitude=data.get("altitude", 0.0),
                accuracy=data.get("accuracy", 0.0),
                timestamp=datetime.now(),
            )
        except (json.JSONDecodeError, KeyError):
            return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_backends.py -v
```
Expected: all 5 PASS

- [ ] **Step 6: Commit**

```bash
git add backends/base.py backends/termux.py tests/test_backends.py
git commit -m "feat: add backend interface and Termux API backend"
```

---

## Task 5: Linux backend skeleton

**Files:**
- Create: `backends/linux.py`

- [ ] **Step 1: Implement backends/linux.py**

```python
# backends/linux.py
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation


class LinuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        raise NotImplementedError("Linux backend: implement using `iw dev <iface> scan`")

    def scan_bluetooth(self) -> list[BTDevice]:
        raise NotImplementedError("Linux backend: implement using hcitool/bluetoothctl")

    def get_location(self) -> GPSLocation | None:
        raise NotImplementedError("Linux backend: implement using gpsd + gpspipe")
```

- [ ] **Step 2: Verify import**

```bash
python -c "from backends.linux import LinuxBackend; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backends/linux.py
git commit -m "feat: add Linux backend skeleton for desktop port"
```

---

## Task 6: WiFi scanner

**Files:**
- Create: `scanners/wifi.py`
- Create: `tests/test_wifi_scanner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_wifi_scanner.py
from unittest.mock import MagicMock
from scanners.wifi import WiFiScanner
from tests.conftest import make_wifi, make_gps


def make_backend(wifi_results):
    backend = MagicMock()
    backend.scan_wifi.return_value = wifi_results
    return backend


def test_first_scan_returns_all_as_appeared():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    scanner = WiFiScanner(make_backend([net]))
    events = scanner.scan(gps=None)
    assert len(events.appeared) == 1
    assert events.appeared[0].bssid == "aa:bb:cc:dd:ee:01"
    assert events.disappeared == []
    assert events.updated == []


def test_second_scan_no_change_returns_empty_events():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    backend = make_backend([net])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    events = scanner.scan(gps=None)
    assert events.appeared == []
    assert events.disappeared == []


def test_disappeared_network_detected():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    backend = make_backend([net])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = []
    events = scanner.scan(gps=None)
    assert len(events.disappeared) == 1
    assert events.disappeared[0].bssid == "aa:bb:cc:dd:ee:01"


def test_significant_rssi_change_produces_updated_event():
    net_weak = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-80)
    net_strong = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-60)
    backend = make_backend([net_weak])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = [net_strong]
    events = scanner.scan(gps=None)
    assert len(events.updated) == 1
    assert events.updated[0].rssi == -60


def test_small_rssi_change_does_not_produce_updated_event():
    net1 = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-60)
    net2 = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-65)
    backend = make_backend([net1])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = [net2]
    events = scanner.scan(gps=None)
    assert events.updated == []


def test_gps_coordinates_attached_to_detections():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01", lat=None, lon=None)
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = WiFiScanner(make_backend([net]))
    events = scanner.scan(gps=gps)
    assert events.appeared[0].lat == 37.77
    assert events.appeared[0].lon == -122.41
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_wifi_scanner.py -v
```
Expected: `ImportError: No module named 'scanners.wifi'`

- [ ] **Step 3: Implement scanners/wifi.py**

```python
# scanners/wifi.py
from dataclasses import dataclass, replace
from models import WiFiNetwork, GPSLocation
from backends.base import BaseBackend

_RSSI_CHANGE_THRESHOLD = 10


@dataclass
class WiFiScanEvents:
    appeared: list[WiFiNetwork]
    disappeared: list[WiFiNetwork]
    updated: list[WiFiNetwork]


class WiFiScanner:
    def __init__(self, backend: BaseBackend):
        self._backend = backend
        self._seen: dict[str, WiFiNetwork] = {}

    def scan(self, gps: GPSLocation | None) -> WiFiScanEvents:
        current = self._backend.scan_wifi()
        if gps:
            current = [replace(n, lat=gps.lat, lon=gps.lon) for n in current]

        current_by_bssid = {n.bssid: n for n in current}
        appeared, disappeared, updated = [], [], []

        for bssid, network in current_by_bssid.items():
            if bssid not in self._seen:
                appeared.append(network)
            elif abs(network.rssi - self._seen[bssid].rssi) >= _RSSI_CHANGE_THRESHOLD:
                updated.append(network)

        for bssid, network in self._seen.items():
            if bssid not in current_by_bssid:
                disappeared.append(network)

        self._seen = current_by_bssid
        return WiFiScanEvents(appeared=appeared, disappeared=disappeared, updated=updated)

    @property
    def current(self) -> list[WiFiNetwork]:
        return list(self._seen.values())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_wifi_scanner.py -v
```
Expected: all 6 PASS

- [ ] **Step 5: Commit**

```bash
git add scanners/wifi.py tests/test_wifi_scanner.py
git commit -m "feat: add WiFi scanner with appear/disappear/rssi-change diffing"
```

---

## Task 7: Bluetooth scanner

**Files:**
- Create: `scanners/bluetooth.py`
- Create: `tests/test_bt_scanner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_bt_scanner.py
from unittest.mock import MagicMock, patch
from scanners.bluetooth import BTScanner
from tests.conftest import make_bt, make_gps


def make_backend(bt_results):
    backend = MagicMock()
    backend.scan_bluetooth.return_value = bt_results
    return backend


def test_first_scan_all_appeared():
    device = make_bt(address="11:22:33:44:55:01")
    scanner = BTScanner(make_backend([device]))
    events = scanner.scan(gps=None)
    assert len(events.appeared) == 1
    assert events.appeared[0].address == "11:22:33:44:55:01"


def test_second_scan_no_change_returns_empty():
    device = make_bt(address="11:22:33:44:55:01")
    backend = make_backend([device])
    scanner = BTScanner(backend)
    scanner.scan(gps=None)
    events = scanner.scan(gps=None)
    assert events.appeared == []
    assert events.disappeared == []


def test_disappeared_device_detected():
    device = make_bt(address="11:22:33:44:55:01")
    backend = make_backend([device])
    scanner = BTScanner(backend)
    scanner.scan(gps=None)
    backend.scan_bluetooth.return_value = []
    events = scanner.scan(gps=None)
    assert len(events.disappeared) == 1


def test_gps_attached_to_bt_detections():
    device = make_bt(address="11:22:33:44:55:01", lat=None, lon=None)
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = BTScanner(make_backend([device]))
    events = scanner.scan(gps=gps)
    assert events.appeared[0].lat == 37.77


def test_vendor_lookup_called_on_new_device():
    device = make_bt(address="40:4d:7f:11:22:33", manufacturer=None)
    with patch("scanners.bluetooth.lookup_vendor", return_value="Apple") as mock_lookup:
        scanner = BTScanner(make_backend([device]))
        events = scanner.scan(gps=None)
    mock_lookup.assert_called_once_with("40:4d:7f:11:22:33")
    assert events.appeared[0].manufacturer == "Apple"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_bt_scanner.py -v
```
Expected: `ImportError: No module named 'scanners.bluetooth'`

- [ ] **Step 3: Implement scanners/bluetooth.py**

```python
# scanners/bluetooth.py
from dataclasses import dataclass, replace
from models import BTDevice, GPSLocation
from backends.base import BaseBackend
from oui import lookup_vendor


@dataclass
class BTScanEvents:
    appeared: list[BTDevice]
    disappeared: list[BTDevice]


class BTScanner:
    def __init__(self, backend: BaseBackend):
        self._backend = backend
        self._seen: dict[str, BTDevice] = {}

    def scan(self, gps: GPSLocation | None) -> BTScanEvents:
        current = self._backend.scan_bluetooth()
        if gps:
            current = [replace(d, lat=gps.lat, lon=gps.lon) for d in current]

        current_by_address = {d.address: d for d in current}
        appeared, disappeared = [], []

        for address, device in current_by_address.items():
            if address not in self._seen:
                vendor = lookup_vendor(address)
                device = replace(device, manufacturer=vendor)
                appeared.append(device)
                self._seen[address] = device

        for address, device in list(self._seen.items()):
            if address not in current_by_address:
                disappeared.append(device)
                del self._seen[address]

        return BTScanEvents(appeared=appeared, disappeared=disappeared)

    @property
    def current(self) -> list[BTDevice]:
        return list(self._seen.values())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_bt_scanner.py -v
```
Expected: all 5 PASS

- [ ] **Step 5: Commit**

```bash
git add scanners/bluetooth.py tests/test_bt_scanner.py
git commit -m "feat: add Bluetooth scanner with OUI vendor lookup"
```

---

## Task 8: GPS scanner

**Files:**
- Create: `scanners/gps.py`
- Create: `tests/test_gps_scanner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gps_scanner.py
from unittest.mock import MagicMock
from scanners.gps import GPSScanner
from tests.conftest import make_gps


def make_backend(location):
    backend = MagicMock()
    backend.get_location.return_value = location
    return backend


def test_returns_none_before_first_poll():
    scanner = GPSScanner(make_backend(None))
    assert scanner.current_location is None


def test_returns_location_after_successful_poll():
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = GPSScanner(make_backend(gps))
    scanner.poll()
    assert scanner.current_location is not None
    assert scanner.current_location.lat == 37.77


def test_retains_last_known_location_when_poll_fails():
    gps = make_gps(lat=37.77, lon=-122.41)
    backend = make_backend(gps)
    scanner = GPSScanner(backend)
    scanner.poll()
    backend.get_location.return_value = None
    scanner.poll()
    assert scanner.current_location.lat == 37.77
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_gps_scanner.py -v
```
Expected: `ImportError: No module named 'scanners.gps'`

- [ ] **Step 3: Implement scanners/gps.py**

```python
# scanners/gps.py
from models import GPSLocation
from backends.base import BaseBackend


class GPSScanner:
    def __init__(self, backend: BaseBackend):
        self._backend = backend
        self._last: GPSLocation | None = None

    def poll(self) -> GPSLocation | None:
        location = self._backend.get_location()
        if location is not None:
            self._last = location
        return self._last

    @property
    def current_location(self) -> GPSLocation | None:
        return self._last
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_gps_scanner.py -v
```
Expected: all 3 PASS

- [ ] **Step 5: Commit**

```bash
git add scanners/gps.py tests/test_gps_scanner.py
git commit -m "feat: add GPS scanner with last-known-fix caching"
```

---

## Task 9: Database storage

**Files:**
- Create: `storage/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_database.py
import pytest
from storage.database import Database
from tests.conftest import make_wifi, make_bt, make_gps


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    yield d
    d.close()


def test_create_session_returns_integer_id(db):
    session_id = db.create_session()
    assert isinstance(session_id, int)


def test_insert_and_retrieve_wifi(db):
    session_id = db.create_session()
    db.insert_wifi(session_id, make_wifi(ssid="HOME-NET", bssid="aa:bb:cc:dd:ee:01"))
    results = db.get_wifi_detections(session_id)
    assert len(results) == 1
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "aa:bb:cc:dd:ee:01"


def test_insert_and_retrieve_bt(db):
    session_id = db.create_session()
    db.insert_bt(session_id, make_bt(name="AirPods", address="11:22:33:44:55:66"))
    results = db.get_bt_detections(session_id)
    assert len(results) == 1
    assert results[0].name == "AirPods"


def test_insert_and_retrieve_gps_track(db):
    session_id = db.create_session()
    db.insert_gps(session_id, make_gps(lat=37.77, lon=-122.41))
    track = db.get_gps_track(session_id)
    assert len(track) == 1
    assert track[0].lat == 37.77


def test_close_session_records_paths(db):
    session_id = db.create_session()
    db.close_session(session_id, kml_path="/tmp/out.kml", gpx_path="/tmp/out.gpx")
    row = db._conn.execute(
        "SELECT ended_at, kml_path FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert row["ended_at"] is not None
    assert row["kml_path"] == "/tmp/out.kml"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_database.py -v
```
Expected: `ImportError: No module named 'storage.database'`

- [ ] **Step 3: Implement storage/database.py**

```python
# storage/database.py
import sqlite3
from datetime import datetime
from models import WiFiNetwork, BTDevice, GPSLocation


class Database:
    def __init__(self, path: str = "civops.db"):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                wifi_count INTEGER DEFAULT 0,
                bt_count INTEGER DEFAULT 0,
                kml_path TEXT,
                gpx_path TEXT
            );
            CREATE TABLE IF NOT EXISTS wifi_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                ssid TEXT, bssid TEXT, rssi INTEGER,
                frequency INTEGER, capabilities TEXT,
                lat REAL, lon REAL, timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS bt_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                name TEXT, address TEXT, rssi INTEGER,
                device_type TEXT, manufacturer TEXT,
                lat REAL, lon REAL, timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS gps_track (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                lat REAL, lon REAL, altitude REAL,
                accuracy REAL, timestamp TEXT
            );
        """)
        self._conn.commit()

    def create_session(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (datetime.now().isoformat(),)
        )
        self._conn.commit()
        return cur.lastrowid

    def close_session(self, session_id: int, kml_path: str, gpx_path: str):
        self._conn.execute(
            "UPDATE sessions SET ended_at=?, kml_path=?, gpx_path=? WHERE id=?",
            (datetime.now().isoformat(), kml_path, gpx_path, session_id)
        )
        self._conn.commit()

    def insert_wifi(self, session_id: int, net: WiFiNetwork):
        self._conn.execute(
            "INSERT INTO wifi_detections "
            "(session_id,ssid,bssid,rssi,frequency,capabilities,lat,lon,timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (session_id, net.ssid, net.bssid, net.rssi, net.frequency,
             net.capabilities, net.lat, net.lon, net.timestamp.isoformat())
        )
        self._conn.commit()

    def insert_bt(self, session_id: int, device: BTDevice):
        self._conn.execute(
            "INSERT INTO bt_detections "
            "(session_id,name,address,rssi,device_type,manufacturer,lat,lon,timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (session_id, device.name, device.address, device.rssi, device.device_type,
             device.manufacturer, device.lat, device.lon, device.timestamp.isoformat())
        )
        self._conn.commit()

    def insert_gps(self, session_id: int, loc: GPSLocation):
        self._conn.execute(
            "INSERT INTO gps_track "
            "(session_id,lat,lon,altitude,accuracy,timestamp) VALUES (?,?,?,?,?,?)",
            (session_id, loc.lat, loc.lon, loc.altitude, loc.accuracy,
             loc.timestamp.isoformat())
        )
        self._conn.commit()

    def get_wifi_detections(self, session_id: int) -> list[WiFiNetwork]:
        rows = self._conn.execute(
            "SELECT * FROM wifi_detections WHERE session_id=?", (session_id,)
        ).fetchall()
        return [WiFiNetwork(
            ssid=r["ssid"], bssid=r["bssid"], rssi=r["rssi"],
            frequency=r["frequency"], capabilities=r["capabilities"],
            lat=r["lat"], lon=r["lon"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def get_bt_detections(self, session_id: int) -> list[BTDevice]:
        rows = self._conn.execute(
            "SELECT * FROM bt_detections WHERE session_id=?", (session_id,)
        ).fetchall()
        return [BTDevice(
            name=r["name"], address=r["address"], rssi=r["rssi"],
            device_type=r["device_type"], manufacturer=r["manufacturer"],
            lat=r["lat"], lon=r["lon"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def get_gps_track(self, session_id: int) -> list[GPSLocation]:
        rows = self._conn.execute(
            "SELECT * FROM gps_track WHERE session_id=?", (session_id,)
        ).fetchall()
        return [GPSLocation(
            lat=r["lat"], lon=r["lon"], altitude=r["altitude"],
            accuracy=r["accuracy"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def close(self):
        self._conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```
Expected: all 5 PASS

- [ ] **Step 5: Commit**

```bash
git add storage/database.py tests/test_database.py
git commit -m "feat: add SQLite storage with WAL mode"
```

---

## Task 10: JSONL logger

**Files:**
- Create: `storage/logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_logger.py
import json
import pytest
from pathlib import Path
from storage.logger import JSONLLogger
from tests.conftest import make_wifi, make_bt, make_gps


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "test.jsonl")


def test_wifi_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_wifi(make_wifi(ssid="HOME-NET", bssid="aa:bb:cc:dd:ee:01"))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "wifi"
    assert data["ssid"] == "HOME-NET"
    assert data["bssid"] == "aa:bb:cc:dd:ee:01"


def test_bt_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_bt(make_bt(name="AirPods"))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "bt"
    assert data["name"] == "AirPods"


def test_gps_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_gps(make_gps(lat=37.77, lon=-122.41))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "gps"
    assert data["lat"] == 37.77


def test_multiple_events_appended_as_separate_lines(log_path):
    logger = JSONLLogger(log_path)
    logger.log_wifi(make_wifi())
    logger.log_bt(make_bt())
    lines = Path(log_path).read_text().strip().split("\n")
    assert len(lines) == 2
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_logger.py -v
```
Expected: `ImportError: No module named 'storage.logger'`

- [ ] **Step 3: Implement storage/logger.py**

```python
# storage/logger.py
import json
from models import WiFiNetwork, BTDevice, GPSLocation


class JSONLLogger:
    def __init__(self, path: str):
        self._path = path

    def log_wifi(self, net: WiFiNetwork):
        self._write({
            "type": "wifi", "ssid": net.ssid, "bssid": net.bssid,
            "rssi": net.rssi, "frequency": net.frequency,
            "capabilities": net.capabilities,
            "lat": net.lat, "lon": net.lon,
            "timestamp": net.timestamp.isoformat(),
        })

    def log_bt(self, device: BTDevice):
        self._write({
            "type": "bt", "name": device.name, "address": device.address,
            "rssi": device.rssi, "device_type": device.device_type,
            "manufacturer": device.manufacturer,
            "lat": device.lat, "lon": device.lon,
            "timestamp": device.timestamp.isoformat(),
        })

    def log_gps(self, loc: GPSLocation):
        self._write({
            "type": "gps", "lat": loc.lat, "lon": loc.lon,
            "altitude": loc.altitude, "accuracy": loc.accuracy,
            "timestamp": loc.timestamp.isoformat(),
        })

    def _write(self, data: dict):
        with open(self._path, "a") as f:
            f.write(json.dumps(data) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_logger.py -v
```
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add storage/logger.py tests/test_logger.py
git commit -m "feat: add JSONL append logger"
```

---

## Task 11: KML export

**Files:**
- Create: `export/kml.py`
- Create: `tests/test_kml.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kml.py
import xml.etree.ElementTree as ET
from export.kml import export_kml
from tests.conftest import make_wifi, make_bt, make_gps

NS = {"kml": "http://www.opengis.net/kml/2.2"}


def test_kml_has_correct_root_element(tmp_path):
    out = str(tmp_path / "out.kml")
    export_kml(wifi=[], bt=[], track=[], path=out)
    root = ET.parse(out).getroot()
    assert root.tag == "{http://www.opengis.net/kml/2.2}kml"


def test_wifi_placemark_created_per_network(tmp_path):
    out = str(tmp_path / "out.kml")
    nets = [
        make_wifi(ssid="NET-A", bssid="aa:bb:cc:00:00:01", lat=37.77, lon=-122.41),
        make_wifi(ssid="NET-B", bssid="aa:bb:cc:00:00:02", lat=37.78, lon=-122.42),
    ]
    export_kml(wifi=nets, bt=[], track=[], path=out)
    placemarks = ET.parse(out).findall(".//kml:Placemark", NS)
    names = [p.find("kml:name", NS).text for p in placemarks]
    assert "NET-A" in names
    assert "NET-B" in names


def test_gps_track_linestring_included(tmp_path):
    out = str(tmp_path / "out.kml")
    track = [make_gps(lat=37.77, lon=-122.41), make_gps(lat=37.78, lon=-122.42)]
    export_kml(wifi=[], bt=[], track=track, path=out)
    assert ET.parse(out).find(".//kml:LineString", NS) is not None


def test_wifi_without_gps_excluded(tmp_path):
    out = str(tmp_path / "out.kml")
    export_kml(wifi=[make_wifi(ssid="NOGPS", lat=None, lon=None)], bt=[], track=[], path=out)
    placemarks = ET.parse(out).findall(".//kml:Placemark", NS)
    names = [p.find("kml:name", NS).text for p in placemarks]
    assert "NOGPS" not in names
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_kml.py -v
```
Expected: `ImportError: No module named 'export.kml'`

- [ ] **Step 3: Implement export/kml.py**

```python
# export/kml.py
import xml.etree.ElementTree as ET
from models import WiFiNetwork, BTDevice, GPSLocation

_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", _NS)


def export_kml(
    wifi: list[WiFiNetwork],
    bt: list[BTDevice],
    track: list[GPSLocation],
    path: str,
):
    kml = ET.Element(f"{{{_NS}}}kml")
    doc = ET.SubElement(kml, f"{{{_NS}}}Document")

    for net in wifi:
        if net.lat is None or net.lon is None:
            continue
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = net.ssid
        ET.SubElement(pm, f"{{{_NS}}}description").text = (
            f"BSSID: {net.bssid}\nRSSI: {net.rssi}dBm\nSecurity: {net.capabilities}"
        )
        pt = ET.SubElement(pm, f"{{{_NS}}}Point")
        ET.SubElement(pt, f"{{{_NS}}}coordinates").text = f"{net.lon},{net.lat},0"

    for device in bt:
        if device.lat is None or device.lon is None:
            continue
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = device.name
        ET.SubElement(pm, f"{{{_NS}}}description").text = (
            f"Address: {device.address}\nRSSI: {device.rssi}dBm\n"
            f"Type: {device.device_type}\nVendor: {device.manufacturer or 'unknown'}"
        )
        pt = ET.SubElement(pm, f"{{{_NS}}}Point")
        ET.SubElement(pt, f"{{{_NS}}}coordinates").text = f"{device.lon},{device.lat},0"

    if track:
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = "GPS Track"
        ls = ET.SubElement(pm, f"{{{_NS}}}LineString")
        ET.SubElement(ls, f"{{{_NS}}}coordinates").text = " ".join(
            f"{loc.lon},{loc.lat},{loc.altitude}" for loc in track
        )

    tree = ET.ElementTree(kml)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_kml.py -v
```
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add export/kml.py tests/test_kml.py
git commit -m "feat: add KML export for Google Maps"
```

---

## Task 12: GPX export

**Files:**
- Create: `export/gpx.py`
- Create: `tests/test_gpx.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gpx.py
import xml.etree.ElementTree as ET
from export.gpx import export_gpx
from tests.conftest import make_wifi, make_bt, make_gps

_NS = "http://www.topografix.com/GPX/1/1"


def test_gpx_has_correct_root(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[], bt=[], track=[], path=out)
    assert ET.parse(out).getroot().tag == f"{{{_NS}}}gpx"


def test_wifi_detection_becomes_waypoint(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[make_wifi(ssid="HOME-NET", lat=37.77, lon=-122.41)], bt=[], track=[], path=out)
    root = ET.parse(out).getroot()
    wpts = root.findall(f"{{{_NS}}}wpt")
    assert len(wpts) == 1
    assert wpts[0].find(f"{{{_NS}}}name").text == "HOME-NET"


def test_gps_track_exported_as_trk_with_trkpts(tmp_path):
    out = str(tmp_path / "out.gpx")
    track = [make_gps(lat=37.77, lon=-122.41), make_gps(lat=37.78, lon=-122.42)]
    export_gpx(wifi=[], bt=[], track=track, path=out)
    root = ET.parse(out).getroot()
    trk = root.find(f"{{{_NS}}}trk")
    assert trk is not None
    assert len(trk.findall(f".//{{{_NS}}}trkpt")) == 2


def test_wifi_without_gps_excluded(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[make_wifi(lat=None, lon=None)], bt=[], track=[], path=out)
    assert ET.parse(out).getroot().findall(f"{{{_NS}}}wpt") == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_gpx.py -v
```
Expected: `ImportError: No module named 'export.gpx'`

- [ ] **Step 3: Implement export/gpx.py**

```python
# export/gpx.py
import xml.etree.ElementTree as ET
from models import WiFiNetwork, BTDevice, GPSLocation

_NS = "http://www.topografix.com/GPX/1/1"
ET.register_namespace("", _NS)


def export_gpx(
    wifi: list[WiFiNetwork],
    bt: list[BTDevice],
    track: list[GPSLocation],
    path: str,
):
    gpx = ET.Element(f"{{{_NS}}}gpx", version="1.1", creator="civops")

    for net in wifi:
        if net.lat is None or net.lon is None:
            continue
        wpt = ET.SubElement(gpx, f"{{{_NS}}}wpt", lat=str(net.lat), lon=str(net.lon))
        ET.SubElement(wpt, f"{{{_NS}}}name").text = net.ssid
        ET.SubElement(wpt, f"{{{_NS}}}desc").text = (
            f"BSSID:{net.bssid} RSSI:{net.rssi}dBm Security:{net.capabilities}"
        )

    for device in bt:
        if device.lat is None or device.lon is None:
            continue
        wpt = ET.SubElement(gpx, f"{{{_NS}}}wpt", lat=str(device.lat), lon=str(device.lon))
        ET.SubElement(wpt, f"{{{_NS}}}name").text = device.name
        ET.SubElement(wpt, f"{{{_NS}}}desc").text = (
            f"Address:{device.address} RSSI:{device.rssi}dBm Type:{device.device_type}"
        )

    if track:
        trk = ET.SubElement(gpx, f"{{{_NS}}}trk")
        ET.SubElement(trk, f"{{{_NS}}}name").text = "CIVOPS Track"
        seg = ET.SubElement(trk, f"{{{_NS}}}trkseg")
        for loc in track:
            trkpt = ET.SubElement(seg, f"{{{_NS}}}trkpt", lat=str(loc.lat), lon=str(loc.lon))
            ET.SubElement(trkpt, f"{{{_NS}}}ele").text = str(loc.altitude)
            ET.SubElement(trkpt, f"{{{_NS}}}time").text = loc.timestamp.isoformat()

    tree = ET.ElementTree(gpx)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_gpx.py -v
```
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add export/gpx.py tests/test_gpx.py
git commit -m "feat: add GPX export for QGIS"
```

---

## Task 13: Log screen

**Files:**
- Create: `ui/log_view.py`

No automated tests — manual verification. Build this before Radar so Radar can reference it.

- [ ] **Step 1: Implement ui/log_view.py**

```python
# ui/log_view.py
from datetime import datetime
from textual.widget import Widget
from textual.widgets import Log, Input, Label
from textual.app import ComposeResult
from textual.binding import Binding

_FILTER_CYCLE = ["all", "wifi", "bt", "gps"]
_FILTER_PREFIXES = {
    "wifi": ("[+WIFI]", "[-WIFI]", "[RSSI]"),
    "bt":   ("[+BT]", "[-BT]", "[+BLE]", "[-BLE]"),
    "gps":  ("[GPS]"),
}


class LogScreen(Widget):
    BINDINGS = [
        Binding("f", "cycle_filter", "Filter"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self._all_events: list[str] = []
        self._filter = "all"
        self._search = ""

    def compose(self) -> ComposeResult:
        yield Label("filter: all | search: ''", id="log-status")
        yield Input(placeholder="search…", id="search-input")
        yield Log(id="event-log", auto_scroll=True)

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False

    def add_event(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"{timestamp} {message}"
        self._all_events.append(entry)
        if self._matches(entry):
            self.query_one("#event-log", Log).write_line(entry)

    def _matches(self, entry: str) -> bool:
        if self._filter != "all":
            prefixes = _FILTER_PREFIXES.get(self._filter, ())
            if not any(p in entry for p in prefixes):
                return False
        if self._search and self._search.lower() not in entry.lower():
            return False
        return True

    def _rerender(self) -> None:
        log = self.query_one("#event-log", Log)
        log.clear()
        for entry in self._all_events:
            if self._matches(entry):
                log.write_line(entry)

    def _update_status(self) -> None:
        self.query_one("#log-status", Label).update(
            f"filter: {self._filter} | search: '{self._search}'"
        )

    def action_cycle_filter(self) -> None:
        idx = _FILTER_CYCLE.index(self._filter)
        self._filter = _FILTER_CYCLE[(idx + 1) % len(_FILTER_CYCLE)]
        self._rerender()
        self._update_status()

    def action_focus_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.display = True
        search_input.focus()

    def action_clear_search(self) -> None:
        self._search = ""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        search_input.display = False
        self._rerender()
        self._update_status()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._search = event.value
        self._rerender()
        self._update_status()
```

- [ ] **Step 2: Commit**

```bash
git add ui/log_view.py
git commit -m "feat: add Log TUI screen"
```

---

## Task 14: Radar screen

**Files:**
- Create: `ui/radar.py`

- [ ] **Step 1: Implement ui/radar.py**

```python
# ui/radar.py
from textual.widget import Widget
from textual.widgets import DataTable, Label
from textual.app import ComposeResult
from scanners.wifi import WiFiScanner
from scanners.bluetooth import BTScanner
from scanners.gps import GPSScanner
from storage.database import Database
from storage.logger import JSONLLogger

_BAR_WIDTH = 9


def _rssi_bar(rssi: int) -> str:
    filled = max(0, min(_BAR_WIDTH, int((rssi + 100) / 100 * _BAR_WIDTH)))
    return "▓" * filled + "░" * (_BAR_WIDTH - filled)


def _rssi_color(rssi: int) -> str:
    if rssi >= -65:
        return "green"
    if rssi >= -80:
        return "yellow"
    return "red"


class RadarScreen(Widget):
    def __init__(
        self,
        wifi_scanner: WiFiScanner,
        bt_scanner: BTScanner,
        gps_scanner: GPSScanner,
        db: Database,
        logger: JSONLLogger,
        session_id: int,
        scan_interval: float,
    ):
        super().__init__()
        self._wifi = wifi_scanner
        self._bt = bt_scanner
        self._gps = gps_scanner
        self._db = db
        self._logger = logger
        self._session_id = session_id
        self._scan_interval = scan_interval

    def compose(self) -> ComposeResult:
        yield Label("GPS: waiting for fix", id="gps-status")
        yield Label("── WiFi ───────────────────────────────────────────", markup=False)
        yield DataTable(id="wifi-table", show_cursor=False)
        yield Label("── Bluetooth ──────────────────────────────────────", markup=False)
        yield DataTable(id="bt-table", show_cursor=False)

    def on_mount(self) -> None:
        wifi_table = self.query_one("#wifi-table", DataTable)
        wifi_table.add_columns("Signal", "SSID", "BSSID", "RSSI", "Freq", "Security", "Vendor")
        bt_table = self.query_one("#bt-table", DataTable)
        bt_table.add_columns("Signal", "Name", "Address", "RSSI", "Type", "Vendor")
        self.set_interval(self._scan_interval, self._do_scan)
        self.set_interval(3.0, self._do_gps_poll)

    def _do_gps_poll(self) -> None:
        loc = self._gps.poll()
        if loc:
            self.query_one("#gps-status", Label).update(
                f"GPS: {loc.lat:.4f},{loc.lon:.4f} ±{loc.accuracy:.0f}m"
            )
            self._db.insert_gps(self._session_id, loc)
            self._logger.log_gps(loc)

    def _do_scan(self) -> None:
        gps = self._gps.current_location
        wifi_events = self._wifi.scan(gps=gps)
        bt_events = self._bt.scan(gps=gps)

        for net in wifi_events.appeared:
            self._db.insert_wifi(self._session_id, net)
            self._logger.log_wifi(net)
            self.app.add_log_event(
                f"[+WIFI] {net.ssid} {net.bssid} {net.rssi}dBm {net.capabilities[:8]}"
            )

        for net in wifi_events.disappeared:
            self.app.add_log_event(f"[-WIFI] {net.ssid} last seen {net.rssi}dBm")

        for net in wifi_events.updated:
            self.app.add_log_event(f"[RSSI] {net.ssid} → {net.rssi}dBm")

        for device in bt_events.appeared:
            self._db.insert_bt(self._session_id, device)
            self._logger.log_bt(device)
            tag = "BLE" if device.device_type == "BLE" else "BT"
            self.app.add_log_event(
                f"[+{tag}] {device.name} {device.address} {device.rssi}dBm"
            )

        for device in bt_events.disappeared:
            self.app.add_log_event(f"[-BT] {device.name} last seen {device.rssi}dBm")

        self._refresh_tables()

    def _refresh_tables(self) -> None:
        wifi_table = self.query_one("#wifi-table", DataTable)
        wifi_table.clear()
        for net in sorted(self._wifi.current, key=lambda n: n.rssi, reverse=True):
            color = _rssi_color(net.rssi)
            security = "⚠ OPEN" if not net.capabilities or net.capabilities == "[]" else net.capabilities[:10]
            wifi_table.add_row(
                _rssi_bar(net.rssi), net.ssid, net.bssid,
                f"[{color}]{net.rssi}[/{color}]",
                str(net.frequency), security, "",
            )
        bt_table = self.query_one("#bt-table", DataTable)
        bt_table.clear()
        for device in sorted(self._bt.current, key=lambda d: d.rssi, reverse=True):
            color = _rssi_color(device.rssi)
            bt_table.add_row(
                _rssi_bar(device.rssi), device.name, device.address,
                f"[{color}]{device.rssi}[/{color}]",
                device.device_type, device.manufacturer or "",
            )
```

- [ ] **Step 2: Commit**

```bash
git add ui/radar.py
git commit -m "feat: add Radar TUI screen with WiFi and BT tables"
```

---

## Task 15: Map screen

**Files:**
- Create: `ui/map_view.py`

- [ ] **Step 1: Implement ui/map_view.py**

```python
# ui/map_view.py
from datetime import datetime
from pathlib import Path
from textual.widget import Widget
from textual.widgets import Static, Label
from textual.app import ComposeResult
from textual.binding import Binding
from storage.database import Database
from export.kml import export_kml
from export.gpx import export_gpx

_MAP_WIDTH = 42
_MAP_HEIGHT = 14


def _render_ascii_track(track, wifi, bt, width=_MAP_WIDTH, height=_MAP_HEIGHT) -> str:
    if not track:
        return "  (no GPS track yet — waiting for fix)"

    lats = [p.lat for p in track]
    lons = [p.lon for p in track]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    lat_range = lat_max - lat_min or 0.001
    lon_range = lon_max - lon_min or 0.001

    grid = [[" " for _ in range(width)] for _ in range(height)]

    def to_xy(lat, lon):
        x = int((lon - lon_min) / lon_range * (width - 1))
        y = int((lat_max - lat) / lat_range * (height - 1))
        return max(0, min(width - 1, x)), max(0, min(height - 1, y))

    for loc in track:
        x, y = to_xy(loc.lat, loc.lon)
        grid[y][x] = "·"

    x, y = to_xy(track[0].lat, track[0].lon)
    grid[y][x] = "★"

    for net in wifi:
        if net.lat and net.lon:
            x, y = to_xy(net.lat, net.lon)
            grid[y][x] = "W"

    for device in bt:
        if device.lat and device.lon:
            x, y = to_xy(device.lat, device.lon)
            grid[y][x] = "B"

    legend = "  · path  ★ start  W wifi  B bt"
    return "\n".join("  " + "".join(row) for row in grid) + "\n" + legend


class MapScreen(Widget):
    BINDINGS = [
        Binding("k", "export_kml", "KML"),
        Binding("g", "export_gpx", "GPX"),
    ]

    def __init__(self, db: Database, session_id: int):
        super().__init__()
        self._db = db
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        yield Static("", id="ascii-map")
        yield Static("", id="session-summary")
        yield Label("", id="export-status")

    def on_mount(self) -> None:
        self.set_interval(5.0, self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        self.query_one("#ascii-map", Static).update(_render_ascii_track(track, wifi, bt))
        open_count = sum(
            1 for n in wifi if not n.capabilities or n.capabilities == "[]"
        )
        self.query_one("#session-summary", Static).update(
            f"WiFi: {len(wifi)}  BT/BLE: {len(bt)}  GPS fixes: {len(track)}"
            + (f"  ⚠ {open_count} open" if open_count else "")
        )

    def _output_path(self, ext: str) -> str:
        base = Path.home() / "civops-data"
        base.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d-%H-%M")
        return str(base / f"civops-{ts}.{ext}")

    def action_export_kml(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        path = self._output_path("kml")
        export_kml(wifi=wifi, bt=bt, track=track, path=path)
        self.query_one("#export-status", Label).update(f"KML saved: {path}")
        self.app.add_log_event(f"[EXPORT] KML → {path}")

    def action_export_gpx(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        path = self._output_path("gpx")
        export_gpx(wifi=wifi, bt=bt, track=track, path=path)
        self.query_one("#export-status", Label).update(f"GPX saved: {path}")
        self.app.add_log_event(f"[EXPORT] GPX → {path}")
```

- [ ] **Step 2: Commit**

```bash
git add ui/map_view.py
git commit -m "feat: add Map TUI screen with ASCII GPS track and export"
```

---

## Task 16: Textual app shell

**Files:**
- Create: `ui/app.py`

- [ ] **Step 1: Implement ui/app.py**

```python
# ui/app.py
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, Footer
from backends.base import BaseBackend
from storage.database import Database
from storage.logger import JSONLLogger
from scanners.wifi import WiFiScanner
from scanners.bluetooth import BTScanner
from scanners.gps import GPSScanner
from ui.radar import RadarScreen
from ui.log_view import LogScreen
from ui.map_view import MapScreen


class CivopsApp(App):
    CSS = "TabbedContent { height: 1fr; }"

    BINDINGS = [
        ("r", "switch_tab('radar')", "Radar"),
        ("l", "switch_tab('log')", "Log"),
        ("m", "switch_tab('map')", "Map"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        backend: BaseBackend,
        db: Database,
        logger: JSONLLogger,
        session_id: int,
        scan_interval: float = 5.0,
    ):
        super().__init__()
        self._backend = backend
        self._db = db
        self._logger = logger
        self._session_id = session_id
        self._scan_interval = scan_interval
        self._wifi_scanner = WiFiScanner(backend)
        self._bt_scanner = BTScanner(backend)
        self._gps_scanner = GPSScanner(backend)

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="radar"):
            with TabPane("RADAR", id="radar"):
                yield RadarScreen(
                    self._wifi_scanner, self._bt_scanner, self._gps_scanner,
                    self._db, self._logger, self._session_id, self._scan_interval,
                )
            with TabPane("LOG", id="log"):
                yield LogScreen()
            with TabPane("MAP", id="map"):
                yield MapScreen(self._db, self._session_id)
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def add_log_event(self, text: str) -> None:
        try:
            self.query_one(LogScreen).add_event(text)
        except Exception:
            pass
```

- [ ] **Step 2: Commit**

```bash
git add ui/app.py
git commit -m "feat: add Textual app shell with tab navigation"
```

---

## Task 17: Entry point + integration

**Files:**
- Create: `civops.py`

- [ ] **Step 1: Implement civops.py**

```python
#!/usr/bin/env python3
# civops.py
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from storage.database import Database
from storage.logger import JSONLLogger
from ui.app import CivopsApp


def _detect_backend():
    if shutil.which("termux-wifi-scaninfo"):
        from backends.termux import TermuxBackend
        return TermuxBackend()
    from backends.linux import LinuxBackend
    return LinuxBackend()


def main():
    parser = argparse.ArgumentParser(description="CIVOPS Recon Radar")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Scan interval in seconds (default: 5)")
    parser.add_argument("--backend", choices=["termux", "linux"],
                        help="Force backend (default: auto-detect)")
    parser.add_argument("--db",
                        default=str(Path.home() / "civops-data" / "civops.db"),
                        help="SQLite database path")
    args = parser.parse_args()

    if args.backend == "termux":
        from backends.termux import TermuxBackend
        backend = TermuxBackend()
    elif args.backend == "linux":
        from backends.linux import LinuxBackend
        backend = LinuxBackend()
    else:
        backend = _detect_backend()

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = Database(args.db)
    session_id = db.create_session()

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M")
    log_path = str(Path.home() / "civops-data" / f"civops-{ts}.jsonl")
    logger = JSONLLogger(log_path)

    app = CivopsApp(
        backend=backend, db=db, logger=logger,
        session_id=session_id, scan_interval=args.interval,
    )
    app.run()

    db.close_session(session_id, kml_path="", gpx_path="")
    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

```bash
chmod +x civops.py
```

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS (29 tests across backends, scanners, storage, export)

- [ ] **Step 4: Launch the TUI to verify it starts**

```bash
python civops.py --backend linux
```
Expected: Textual TUI opens with three tabs (RADAR / LOG / MAP). Radar tables are empty (Linux backend raises NotImplementedError on first scan — that's expected). Press `r`, `l`, `m` to switch tabs. Press `q` to quit cleanly. No tracebacks.

- [ ] **Step 5: Commit**

```bash
git add civops.py
git commit -m "feat: add entry point with auto-backend detection"
```

---

## Termux Install Instructions

On your Android device with Termux:

```bash
pkg update && pkg install python termux-api
pip install textual
# clone or copy civops/ to your device, then:
python civops.py
```

Grant permissions when prompted: Location (for GPS + WiFi scan), Bluetooth.
