# tests/test_gps_scanner.py
from unittest.mock import MagicMock
from scanners.gps import GPSScanner
from tests.conftest import make_gps


def make_backend(location):
    backend = MagicMock()
    backend.get_location.return_value = location
    return backend


def test_returns_none_before_first_poll():
    scanner = GPSScanner(make_backend(None))
    assert scanner.current_location is None


def test_returns_location_after_successful_poll():
    gps = make_gps(lat=37.77, lon=-122.41)
    scanner = GPSScanner(make_backend(gps))
    scanner.poll()
    assert scanner.current_location is not None
    assert scanner.current_location.lat == 37.77


def test_retains_last_known_location_when_poll_fails():
    gps = make_gps(lat=37.77, lon=-122.41)
    backend = make_backend(gps)
    scanner = GPSScanner(backend)
    scanner.poll()
    backend.get_location.return_value = None
    scanner.poll()
    assert scanner.current_location.lat == 37.77
