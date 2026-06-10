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
