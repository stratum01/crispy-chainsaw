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
