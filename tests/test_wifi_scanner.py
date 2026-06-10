# tests/test_wifi_scanner.py
from unittest.mock import MagicMock
from scanners.wifi import WiFiScanner
from tests.conftest import make_wifi, make_gps


def make_backend(wifi_results):
    backend = MagicMock()
    backend.scan_wifi.return_value = wifi_results
    return backend


def test_first_scan_returns_all_as_appeared():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    scanner = WiFiScanner(make_backend([net]))
    events = scanner.scan(gps=None)
    assert len(events.appeared) == 1
    assert events.appeared[0].bssid == "aa:bb:cc:dd:ee:01"
    assert events.disappeared == []
    assert events.updated == []


def test_second_scan_no_change_returns_empty_events():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    backend = make_backend([net])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    events = scanner.scan(gps=None)
    assert events.appeared == []
    assert events.disappeared == []


def test_disappeared_network_detected():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01")
    backend = make_backend([net])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = []
    events = scanner.scan(gps=None)
    assert len(events.disappeared) == 1
    assert events.disappeared[0].bssid == "aa:bb:cc:dd:ee:01"


def test_significant_rssi_change_produces_updated_event():
    net_weak = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-80)
    net_strong = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-60)
    backend = make_backend([net_weak])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = [net_strong]
    events = scanner.scan(gps=None)
    assert len(events.updated) == 1
    assert events.updated[0].rssi == -60


def test_small_rssi_change_does_not_produce_updated_event():
    net1 = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-60)
    net2 = make_wifi(bssid="aa:bb:cc:dd:ee:01", rssi=-65)
    backend = make_backend([net1])
    scanner = WiFiScanner(backend)
    scanner.scan(gps=None)
    backend.scan_wifi.return_value = [net2]
    events = scanner.scan(gps=None)
    assert events.updated == []


def test_gps_coordinates_attached_to_detections():
    net = make_wifi(bssid="aa:bb:cc:dd:ee:01", lat=None, lon=None)
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = WiFiScanner(make_backend([net]))
    events = scanner.scan(gps=gps)
    assert events.appeared[0].lat == 37.77
    assert events.appeared[0].lon == -122.41
