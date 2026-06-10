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
