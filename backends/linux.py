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
