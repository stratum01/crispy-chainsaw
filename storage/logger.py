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
