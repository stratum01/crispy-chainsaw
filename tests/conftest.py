# tests/conftest.py
from datetime import datetime
from models import WiFiNetwork, BTDevice, GPSLocation


def make_wifi(**kwargs):
    defaults = dict(
        ssid="TEST-NET", bssid="aa:bb:cc:dd:ee:ff", rssi=-60,
        frequency=2437, capabilities="WPA2",
        lat=37.7749, lon=-122.4194, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return WiFiNetwork(**{**defaults, **kwargs})


def make_bt(**kwargs):
    defaults = dict(
        name="TestDevice", address="11:22:33:44:55:66", rssi=-65,
        device_type="Classic", manufacturer="Apple",
        lat=37.7749, lon=-122.4194, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return BTDevice(**{**defaults, **kwargs})


def make_gps(**kwargs):
    defaults = dict(
        lat=37.7749, lon=-122.4194, altitude=12.0,
        accuracy=8.0, timestamp=datetime(2026, 6, 10, 12, 0, 0),
    )
    return GPSLocation(**{**defaults, **kwargs})
