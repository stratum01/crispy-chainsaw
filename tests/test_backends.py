# tests/test_backends.py
import json
import subprocess
from unittest.mock import patch, AsyncMock, MagicMock
from backends.termux import TermuxBackend
from backends.linux import LinuxBackend
from models import WiFiNetwork, BTDevice, GPSLocation

WIFI_JSON = json.dumps([{
    "ssid": "HOME-NET", "bssid": "bc:ae:c5:12:34:56",
    "rssi": -52, "frequency": 2437, "capabilities": "[WPA2-PSK-CCMP][ESS]"
}])
BT_JSON = json.dumps([{
    "name": "AirPods Pro", "address": "40:4D:7F:11:22:33",
    "rssi": -55, "type": 1
}])
GPS_JSON = json.dumps({
    "latitude": 37.7749, "longitude": -122.4194,
    "altitude": 12.0, "accuracy": 8.0
})


def test_termux_scan_wifi_returns_wifi_networks():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = WIFI_JSON
        mock_run.return_value.returncode = 0
        results = TermuxBackend().scan_wifi()
    assert len(results) == 1
    assert isinstance(results[0], WiFiNetwork)
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "bc:ae:c5:12:34:56"
    assert results[0].rssi == -52


def test_termux_scan_bluetooth_returns_bt_devices():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = BT_JSON
        mock_run.return_value.returncode = 0
        results = TermuxBackend().scan_bluetooth()
    assert len(results) == 1
    assert isinstance(results[0], BTDevice)
    assert results[0].name == "AirPods Pro"
    assert results[0].device_type == "Classic"


def test_termux_get_location_returns_gps_location():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = GPS_JSON
        mock_run.return_value.returncode = 0
        loc = TermuxBackend().get_location()
    assert isinstance(loc, GPSLocation)
    assert loc.lat == 37.7749
    assert loc.lon == -122.4194


def test_termux_get_location_returns_none_on_failure():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        loc = TermuxBackend().get_location()
    assert loc is None


def test_termux_scan_wifi_returns_empty_on_failure():
    with patch("backends.termux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        results = TermuxBackend().scan_wifi()
    assert results == []


_NMCLI_THREE_NETS = (
    "HOME-NET:bc\\:ae\\:c5\\:12\\:34\\:56:85:WPA2\n"
    ":dd\\:ee\\:ff\\:00\\:11\\:22:60:WPA1 WPA2\n"
    "OpenWifi:11\\:22\\:33\\:44\\:55\\:66:40:\n"
)


def test_linux_scan_wifi_returns_wifi_networks():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = _NMCLI_THREE_NETS
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert len(results) == 3
    assert isinstance(results[0], WiFiNetwork)
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "bc:ae:c5:12:34:56"
    assert results[0].rssi == -58   # int(85 * 0.5) - 100
    assert results[0].capabilities == "WPA2"


def test_linux_scan_wifi_hidden_ssid():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = ":dd\\:ee\\:ff\\:00\\:11\\:22:60:WPA1 WPA2\n"
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert results[0].ssid == ""
    assert results[0].bssid == "dd:ee:ff:00:11:22"


def test_linux_scan_wifi_open_network():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "OpenWifi:11\\:22\\:33\\:44\\:55\\:66:40:\n"
        mock_run.return_value.returncode = 0
        results = LinuxBackend().scan_wifi()
    assert results[0].capabilities == ""


def test_linux_scan_wifi_returns_empty_on_nonzero_returncode():
    with patch("backends.linux.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert LinuxBackend().scan_wifi() == []


def test_linux_scan_wifi_returns_empty_when_nmcli_missing():
    with patch("backends.linux.subprocess.run", side_effect=FileNotFoundError()):
        assert LinuxBackend().scan_wifi() == []


def test_linux_scan_wifi_returns_empty_on_timeout():
    with patch("backends.linux.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd="nmcli", timeout=15)):
        assert LinuxBackend().scan_wifi() == []
