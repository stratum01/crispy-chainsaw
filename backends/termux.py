# backends/termux.py
import json
import subprocess
from datetime import datetime
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation

_BT_TYPE_MAP = {1: "Classic", 2: "BLE", 3: "BLE"}


class TermuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        try:
            result = subprocess.run(
                ["termux-wifi-scaninfo"], capture_output=True, text=True
            )
        except FileNotFoundError:
            return []
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
        try:
            result = subprocess.run(
                ["termux-bluetooth-scan", "-d", "4"], capture_output=True, text=True
            )
        except FileNotFoundError:
            return []
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
        try:
            result = subprocess.run(
                ["termux-location", "-p", "gps"], capture_output=True, text=True
            )
        except FileNotFoundError:
            return None
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
