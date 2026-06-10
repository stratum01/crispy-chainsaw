# tests/test_logger.py
import json
import pytest
from pathlib import Path
from storage.logger import JSONLLogger
from tests.conftest import make_wifi, make_bt, make_gps


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "test.jsonl")


def test_wifi_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_wifi(make_wifi(ssid="HOME-NET", bssid="aa:bb:cc:dd:ee:01"))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "wifi"
    assert data["ssid"] == "HOME-NET"
    assert data["bssid"] == "aa:bb:cc:dd:ee:01"


def test_bt_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_bt(make_bt(name="AirPods"))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "bt"
    assert data["name"] == "AirPods"


def test_gps_event_written_as_json_line(log_path):
    JSONLLogger(log_path).log_gps(make_gps(lat=37.77, lon=-122.41))
    data = json.loads(Path(log_path).read_text().strip())
    assert data["type"] == "gps"
    assert data["lat"] == 37.77


def test_multiple_events_appended_as_separate_lines(log_path):
    logger = JSONLLogger(log_path)
    logger.log_wifi(make_wifi())
    logger.log_bt(make_bt())
    lines = Path(log_path).read_text().strip().split("\n")
    assert len(lines) == 2
