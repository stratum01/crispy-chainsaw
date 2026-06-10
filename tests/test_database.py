# tests/test_database.py
import pytest
from storage.database import Database
from tests.conftest import make_wifi, make_bt, make_gps


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    yield d
    d.close()


def test_create_session_returns_integer_id(db):
    session_id = db.create_session()
    assert isinstance(session_id, int)


def test_insert_and_retrieve_wifi(db):
    session_id = db.create_session()
    db.insert_wifi(session_id, make_wifi(ssid="HOME-NET", bssid="aa:bb:cc:dd:ee:01"))
    results = db.get_wifi_detections(session_id)
    assert len(results) == 1
    assert results[0].ssid == "HOME-NET"
    assert results[0].bssid == "aa:bb:cc:dd:ee:01"


def test_insert_and_retrieve_bt(db):
    session_id = db.create_session()
    db.insert_bt(session_id, make_bt(name="AirPods", address="11:22:33:44:55:66"))
    results = db.get_bt_detections(session_id)
    assert len(results) == 1
    assert results[0].name == "AirPods"


def test_insert_and_retrieve_gps_track(db):
    session_id = db.create_session()
    db.insert_gps(session_id, make_gps(lat=37.77, lon=-122.41))
    track = db.get_gps_track(session_id)
    assert len(track) == 1
    assert track[0].lat == 37.77


def test_close_session_records_paths(db):
    session_id = db.create_session()
    db.close_session(session_id, kml_path="/tmp/out.kml", gpx_path="/tmp/out.gpx")
    row = db._conn.execute(
        "SELECT ended_at, kml_path FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert row["ended_at"] is not None
    assert row["kml_path"] == "/tmp/out.kml"
