import xml.etree.ElementTree as ET
from export.gpx import export_gpx
from tests.conftest import make_wifi, make_bt, make_gps

_NS = "http://www.topografix.com/GPX/1/1"


def test_gpx_has_correct_root(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[], bt=[], track=[], path=out)
    assert ET.parse(out).getroot().tag == f"{{{_NS}}}gpx"


def test_wifi_detection_becomes_waypoint(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[make_wifi(ssid="HOME-NET", lat=37.77, lon=-122.41)], bt=[], track=[], path=out)
    root = ET.parse(out).getroot()
    wpts = root.findall(f"{{{_NS}}}wpt")
    assert len(wpts) == 1
    assert wpts[0].find(f"{{{_NS}}}name").text == "HOME-NET"


def test_gps_track_exported_as_trk_with_trkpts(tmp_path):
    out = str(tmp_path / "out.gpx")
    track = [make_gps(lat=37.77, lon=-122.41), make_gps(lat=37.78, lon=-122.42)]
    export_gpx(wifi=[], bt=[], track=track, path=out)
    root = ET.parse(out).getroot()
    trk = root.find(f"{{{_NS}}}trk")
    assert trk is not None
    assert len(trk.findall(f".//{{{_NS}}}trkpt")) == 2


def test_wifi_without_gps_excluded(tmp_path):
    out = str(tmp_path / "out.gpx")
    export_gpx(wifi=[make_wifi(lat=None, lon=None)], bt=[], track=[], path=out)
    assert ET.parse(out).getroot().findall(f"{{{_NS}}}wpt") == []
