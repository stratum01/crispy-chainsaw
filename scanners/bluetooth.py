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
