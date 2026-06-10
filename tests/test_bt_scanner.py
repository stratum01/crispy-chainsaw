# tests/test_bt_scanner.py
from unittest.mock import MagicMock, patch
from scanners.bluetooth import BTScanner
from tests.conftest import make_bt, make_gps


def make_backend(bt_results):
    backend = MagicMock()
    backend.scan_bluetooth.return_value = bt_results
    return backend


def test_first_scan_all_appeared():
    device = make_bt(address="11:22:33:44:55:01")
    scanner = BTScanner(make_backend([device]))
    events = scanner.scan(gps=None)
    assert len(events.appeared) == 1
    assert events.appeared[0].address == "11:22:33:44:55:01"


def test_second_scan_no_change_returns_empty():
    device = make_bt(address="11:22:33:44:55:01")
    backend = make_backend([device])
    scanner = BTScanner(backend)
    scanner.scan(gps=None)
    events = scanner.scan(gps=None)
    assert events.appeared == []
    assert events.disappeared == []


def test_disappeared_device_detected():
    device = make_bt(address="11:22:33:44:55:01")
    backend = make_backend([device])
    scanner = BTScanner(backend)
    scanner.scan(gps=None)
    backend.scan_bluetooth.return_value = []
    events = scanner.scan(gps=None)
    assert len(events.disappeared) == 1


def test_gps_attached_to_bt_detections():
    device = make_bt(address="11:22:33:44:55:01", lat=None, lon=None)
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = BTScanner(make_backend([device]))
    events = scanner.scan(gps=gps)
    assert events.appeared[0].lat == 37.77


def test_vendor_lookup_called_on_new_device():
    device = make_bt(address="40:4d:7f:11:22:33", manufacturer=None)
    with patch("scanners.bluetooth.lookup_vendor", return_value="Apple") as mock_lookup:
        scanner = BTScanner(make_backend([device]))
        events = scanner.scan(gps=None)
    mock_lookup.assert_called_once_with("40:4d:7f:11:22:33")
    assert events.appeared[0].manufacturer == "Apple"
