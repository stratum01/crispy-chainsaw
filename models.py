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
