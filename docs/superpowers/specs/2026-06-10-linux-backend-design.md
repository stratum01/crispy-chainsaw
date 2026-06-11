# Linux Backend Design

## Goal

Implement `backends/linux.py` so CIVOPS Recon Radar runs on an Ubuntu/Debian laptop, scanning WiFi and Bluetooth without root access.

## Scope

- WiFi scanning via `nmcli` subprocess
- Bluetooth LE scanning via `bleak` Python library
- GPS returns `None` (no GPS hardware assumed; web UI already handles this gracefully)
- Target platform: Ubuntu / Debian desktop, normal user account

## Architecture

Only one file changes: `backends/linux.py`. All other files (scanners, storage, web UI, export) are already platform-agnostic. One new dependency: `bleak>=0.21` added to `requirements.txt`.

```
backends/linux.py   ← only file modified
requirements.txt    ← add bleak>=0.21
```

## WiFi Implementation

### Command

```
nmcli -t -f SSID,BSSID,SIGNAL,SECURITY dev wifi list --rescan yes
```

- `--rescan yes`: forces a fresh scan each call (blocks ~2–5s while NM scans)
- `-t`: terse mode, colon-separated fields, colons inside values escaped as `\:`
- No root required; NetworkManager handles the scan

### Output format

```
MyNetwork:AA\:BB\:CC\:DD\:EE\:FF:85:WPA2
:11\:22\:33\:44\:55\:66:60:WPA1 WPA2
OpenCafe:33\:44\:55\:66\:77\:88:45:
```

Fields: SSID, BSSID, SIGNAL (0–100%), SECURITY

### Parsing

Split each line using `re.split(r'(?<!\\):', line)` to handle unescaped colons only, then unescape `\:` in each field. Yields exactly 4 fields per line; skip malformed lines.

### RSSI conversion

nmcli SIGNAL is a percentage (0–100). Convert to approximate dBm:

```
rssi_dbm = int(signal_pct * 0.5) - 100
```

Range: -100 dBm (0%) to -50 dBm (100%). This is an approximation — NetworkManager does not expose per-network dBm without root. Sufficient for display, color coding, and signal bars.

### Security field

- Empty string or `--` → `""` (treated as open by web UI)
- Any other value → pass through as-is (e.g., `WPA2`, `WPA1 WPA2`, `WPA3`)

### Error handling

Wrap the subprocess call in `try/except`. Return `[]` on `FileNotFoundError` (nmcli not installed), `subprocess.TimeoutExpired`, or any other exception.

## Bluetooth Implementation

### Library

`bleak>=0.21` — modern BLE library, pip-installable, wraps BlueZ D-Bus API via `dbus-fast` (pure Python, no system packages needed).

**BLE only**: classic Bluetooth (BR/EDR) devices are not detected. For security research, BLE is the primary surface (phones, IoT, wearables). Classic BT can be added later if needed.

### Scan approach

A 3-second BLE discovery scan per `scan_bluetooth()` call:

```python
async def _discover():
    return await BleakScanner.discover(timeout=3.0)

def scan_bluetooth(self) -> list[BTDevice]:
    loop = asyncio.new_event_loop()
    try:
        ble_devices = loop.run_until_complete(_discover())
    except Exception:
        return []
    finally:
        loop.close()
```

A new event loop per call is correct here — `scan_bluetooth()` is called from a regular (non-async) thread in the web UI's background scan thread.

### Device fields

| BTDevice field | Source |
|---|---|
| `name` | `device.name` or `"(unknown)"` if None |
| `address` | `device.address` (MAC) |
| `rssi` | `device.rssi` — real dBm from BLE advertising packets |
| `device_type` | Always `"BLE"` on this backend |
| `manufacturer` | `None` — scanner layer calls `lookup_vendor()` after backend returns |

### Error handling

Any exception from bleak (permission error, no adapter, D-Bus unavailable) → return `[]`. Print a one-line warning to stderr on first failure so the user knows BT is unavailable.

## GPS

```python
def get_location(self) -> None:
    return None
```

The web UI displays "GPS: waiting for fix" when `gps` is `None`. No change needed elsewhere.

## System Setup (one-time, Ubuntu/Debian)

WiFi requires no setup — `nmcli` is installed by default with NetworkManager on Ubuntu desktop.

Bluetooth requires:
```bash
sudo usermod -aG bluetooth $USER
# log out and back in for group membership to take effect
```

Without bluetooth group membership, BlueZ rejects `StartDiscovery` with a D-Bus permission error — caught gracefully, BT returns `[]`.

## Dependency change

```
# requirements.txt — add:
bleak>=0.21
```

## Running on Linux

```bash
pip install flask textual bleak
python civops.py --web --backend linux
# or let auto-detect pick it up (no termux-wifi-scaninfo on Linux)
python civops.py --web
```

## Limitations

- WiFi RSSI is approximate (percentage → dBm conversion, not actual measured dBm)
- Bluetooth is BLE only (no classic BR/EDR)
- No GPS (returns None)
- WiFi `--rescan yes` blocks the scan thread for ~2–5s per cycle; scan interval should be set ≥10s on Linux (`--interval 10`)
