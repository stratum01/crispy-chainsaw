# Linux Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `backends/linux.py` so CIVOPS runs on Ubuntu/Debian, scanning WiFi via nmcli and BLE devices via bleak.

**Architecture:** `LinuxBackend` subclasses `BaseBackend` and implements all three abstract methods. WiFi uses a subprocess call to `nmcli` with output parsing; Bluetooth uses the `bleak` BLE library (wraps BlueZ D-Bus) running in a fresh asyncio event loop; GPS returns `None`. No other files need to change except `requirements.txt` (add `bleak>=0.21`) and `tests/test_backends.py` (new Linux tests).

**Tech Stack:** Python 3.11+, `nmcli` (system, pre-installed on Ubuntu), `bleak>=0.21` (pip), `asyncio`, `re`, `subprocess`

---

## File Structure

- Modify: `backends/linux.py` — replace NotImplementedError stubs with full implementation
- Modify: `requirements.txt` — add `bleak>=0.21`
- Modify: `tests/test_backends.py` — add Linux backend test cases

---

### Task 1: WiFi scanning

**Files:**
- Modify: `requirements.txt`
- Modify: `backends/linux.py`
- Modify: `tests/test_backends.py`

- [ ] **Step 1: Add bleak to requirements.txt**

Open `requirements.txt`. It currently reads:
```
textual>=0.50,<1.0
flask>=3.0
pytest>=7.0
```

Replace it with:
```
textual>=0.50,<1.0
flask>=3.0
pytest>=7.0
bleak>=0.21
```

- [ ] **Step 2: Install bleak**

```bash
pip install bleak>=0.21
```

Expected: bleak and its dependencies (dbus-fast, etc.) install without error.

- [ ] **Step 3: Write the failing WiFi tests**

First, add two imports to the existing import block at the top of `tests/test_backends.py` (the file already has `from unittest.mock import patch` and `from models import WiFiNetwork, BTDevice, GPSLocation`):

```python
from unittest.mock import AsyncMock, MagicMock  # add to existing mock import line
from backends.linux import LinuxBackend          # add after TermuxBackend import
```

Then add to the bottom of `tests/test_backends.py`:

```python
_NMCLI_THREE_NETS = (
    "HOME-NET:bc\\:ae\\:c5\\:12\\:34\\:56:85:WPA2\n"
    ":dd\\:ee\\:ff\\:00\\:11\\:22:60:WPA1 WPA2\n"
    "OpenWifi:11\\:22\\:33\\:44\\:55\\:66:40:\n"
)


def test_linux_scan_wifi_returns_wifi_networks():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = _NMCLI_THREE_NETS
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert len(results) == 3
    assert isinstance(results[0], WiFiNetwork)
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "bc:ae:c5:12:34:56"
    assert results[0].rssi == -58   # int(85 * 0.5) - 100
    assert results[0].capabilities == "WPA2"


def test_linux_scan_wifi_hidden_ssid():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = ":dd\\:ee\\:ff\\:00\\:11\\:22:60:WPA1 WPA2\n"
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert results[0].ssid == ""
    assert results[0].bssid == "dd:ee:ff:00:11:22"


def test_linux_scan_wifi_open_network():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "OpenWifi:11\\:22\\:33\\:44\\:55\\:66:40:\n"
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert results[0].capabilities == ""


def test_linux_scan_wifi_returns_empty_on_nonzero_returncode():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert LinuxBackend().scan_wifi() == []


def test_linux_scan_wifi_returns_empty_when_nmcli_missing():
    with patch("backends.linux.subprocess.run", side_effect=FileNotFoundError()):
        assert LinuxBackend().scan_wifi() == []
```

- [ ] **Step 4: Run the tests to verify they fail**

```bash
cd /home/stratum/civops
pytest tests/test_backends.py::test_linux_scan_wifi_returns_wifi_networks -v
```

Expected: `FAILED` — `NotImplementedError: Linux backend: implement using...`

- [ ] **Step 5: Implement scan_wifi() in backends/linux.py**

Replace the entire contents of `backends/linux.py` with:

```python
# backends/linux.py
import re
import subprocess
from datetime import datetime
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation


def _signal_to_rssi(signal_pct: int) -> int:
    return int(signal_pct * 0.5) - 100


class LinuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,SECURITY",
                 "dev", "wifi", "list", "--rescan", "yes"],
                capture_output=True, text=True, timeout=15,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0:
            return []
        networks = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'(?<!\\):', line)
            if len(parts) < 4:
                continue
            ssid = parts[0].replace('\\:', ':')
            bssid = parts[1].replace('\\:', ':')
            try:
                signal_pct = int(parts[2])
            except ValueError:
                continue
            security = parts[3].strip()
            if security == '--':
                security = ''
            networks.append(WiFiNetwork(
                ssid=ssid,
                bssid=bssid,
                rssi=_signal_to_rssi(signal_pct),
                frequency=0,
                capabilities=security,
                lat=None,
                lon=None,
                timestamp=datetime.now(),
            ))
        return networks

    def scan_bluetooth(self) -> list[BTDevice]:
        raise NotImplementedError("implement in Task 2")

    def get_location(self) -> GPSLocation | None:
        raise NotImplementedError("implement in Task 2")
```

- [ ] **Step 6: Run the WiFi tests to verify they pass**

```bash
pytest tests/test_backends.py -k "linux_scan_wifi" -v
```

Expected: 5 tests PASSED.

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
pytest tests/ -v
```

Expected: all previously passing tests still pass; the new 5 Linux WiFi tests pass. The two `test_linux_scan_bluetooth_*` and `test_linux_get_location_*` tests don't exist yet — that's fine.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt backends/linux.py tests/test_backends.py
git commit -m "feat: implement LinuxBackend.scan_wifi() via nmcli"
```

---

### Task 2: Bluetooth scanning and GPS stub

**Files:**
- Modify: `backends/linux.py` — add BLE scanning + GPS stub, add bleak import
- Modify: `tests/test_backends.py` — add BT + GPS tests

- [ ] **Step 1: Write the failing BT and GPS tests**

Add to the bottom of `tests/test_backends.py`:

```python
def test_linux_scan_bluetooth_returns_bt_devices():
    mock_dev = MagicMock()
    mock_dev.name = "TestPhone"
    mock_dev.address = "AA:BB:CC:DD:EE:FF"
    mock_dev.rssi = -62
    with patch("backends.linux.BleakScanner.discover",
               new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = [mock_dev]
        results = LinuxBackend().scan_bluetooth()
    assert len(results) == 1
    assert isinstance(results[0], BTDevice)
    assert results[0].name == "TestPhone"
    assert results[0].address == "AA:BB:CC:DD:EE:FF"
    assert results[0].rssi == -62
    assert results[0].device_type == "BLE"
    assert results[0].manufacturer is None


def test_linux_scan_bluetooth_none_name_becomes_unknown():
    mock_dev = MagicMock()
    mock_dev.name = None
    mock_dev.address = "BB:CC:DD:EE:FF:00"
    mock_dev.rssi = -75
    with patch("backends.linux.BleakScanner.discover",
               new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = [mock_dev]
        results = LinuxBackend().scan_bluetooth()
    assert results[0].name == "(unknown)"


def test_linux_scan_bluetooth_returns_empty_on_exception():
    with patch("backends.linux.BleakScanner.discover",
               new_callable=AsyncMock) as mock_disc:
        mock_disc.side_effect = Exception("No BT adapter")
        assert LinuxBackend().scan_bluetooth() == []


def test_linux_get_location_returns_none():
    assert LinuxBackend().get_location() is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_backends.py -k "linux_scan_bluetooth or linux_get_location" -v
```

Expected: `FAILED` — `NotImplementedError: implement in Task 2` (or ImportError if BleakScanner not yet imported).

- [ ] **Step 3: Implement scan_bluetooth() and get_location() in backends/linux.py**

Replace the entire contents of `backends/linux.py` with:

```python
# backends/linux.py
import asyncio
import re
import subprocess
from datetime import datetime
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation
from bleak import BleakScanner


def _signal_to_rssi(signal_pct: int) -> int:
    return int(signal_pct * 0.5) - 100


class LinuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,SECURITY",
                 "dev", "wifi", "list", "--rescan", "yes"],
                capture_output=True, text=True, timeout=15,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0:
            return []
        networks = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'(?<!\\):', line)
            if len(parts) < 4:
                continue
            ssid = parts[0].replace('\\:', ':')
            bssid = parts[1].replace('\\:', ':')
            try:
                signal_pct = int(parts[2])
            except ValueError:
                continue
            security = parts[3].strip()
            if security == '--':
                security = ''
            networks.append(WiFiNetwork(
                ssid=ssid,
                bssid=bssid,
                rssi=_signal_to_rssi(signal_pct),
                frequency=0,
                capabilities=security,
                lat=None,
                lon=None,
                timestamp=datetime.now(),
            ))
        return networks

    def scan_bluetooth(self) -> list[BTDevice]:
        try:
            loop = asyncio.new_event_loop()
            try:
                ble_devices = loop.run_until_complete(
                    BleakScanner.discover(timeout=3.0)
                )
            finally:
                loop.close()
        except Exception:
            return []
        devices = []
        for d in ble_devices:
            devices.append(BTDevice(
                name=d.name or "(unknown)",
                address=d.address,
                rssi=d.rssi if d.rssi is not None else -80,
                device_type="BLE",
                manufacturer=None,
                lat=None,
                lon=None,
                timestamp=datetime.now(),
            ))
        return devices

    def get_location(self) -> GPSLocation | None:
        return None
```

- [ ] **Step 4: Run the BT and GPS tests to verify they pass**

```bash
pytest tests/test_backends.py -k "linux_scan_bluetooth or linux_get_location" -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. Count should be previous total + 9 new Linux tests.

- [ ] **Step 6: Smoke test on the laptop**

```bash
cd /home/stratum/civops
python civops.py --web --backend linux --interval 15
```

Open `http://localhost:8080` in a browser. You should see WiFi networks listed with signal bars. BLE devices appear after a few scan cycles (bleak scans for 3s per cycle). GPS section shows "GPS: waiting for fix" — expected.

If WiFi shows empty, check `nmcli dev wifi list` runs without error in your terminal. If BLE shows empty after 30s, verify you're in the bluetooth group (`groups | grep bluetooth`) and have logged out/in since running `usermod`.

- [ ] **Step 7: Commit**

```bash
git add backends/linux.py tests/test_backends.py
git commit -m "feat: implement LinuxBackend.scan_bluetooth() via bleak and GPS stub"
```
