import xml.etree.ElementTree as ET
from export.kml import export_kml
from tests.conftest import make_wifi, make_bt, make_gps

NS = {"kml": "http://www.opengis.net/kml/2.2"}


def test_kml_has_correct_root_element(tmp_path):
    out = str(tmp_path / "out.kml")
    export_kml(wifi=[], bt=[], track=[], path=out)
    root = ET.parse(out).getroot()
    assert root.tag == "{http://www.opengis.net/kml/2.2}kml"


def test_wifi_placemark_created_per_network(tmp_path):
    out = str(tmp_path / "out.kml")
    nets = [
        make_wifi(ssid="NET-A", bssid="aa:bb:cc:00:00:01", lat=37.77, lon=-122.41),
        make_wifi(ssid="NET-B", bssid="aa:bb:cc:00:00:02", lat=37.78, lon=-122.42),
    ]
    export_kml(wifi=nets, bt=[], track=[], path=out)
    placemarks = ET.parse(out).findall(".//kml:Placemark", NS)
    names = [p.find("kml:name", NS).text for p in placemarks]
    assert "NET-A" in names
    assert "NET-B" in names


def test_gps_track_linestring_included(tmp_path):
    out = str(tmp_path / "out.kml")
    track = [make_gps(lat=37.77, lon=-122.41), make_gps(lat=37.78, lon=-122.42)]
    export_kml(wifi=[], bt=[], track=track, path=out)
    assert ET.parse(out).find(".//kml:LineString", NS) is not None


def test_wifi_without_gps_excluded(tmp_path):
    out = str(tmp_path / "out.kml")
    export_kml(wifi=[make_wifi(ssid="NOGPS", lat=None, lon=None)], bt=[], track=[], path=out)
    placemarks = ET.parse(out).findall(".//kml:Placemark", NS)
    names = [p.find("kml:name", NS).text for p in placemarks]
    assert "NOGPS" not in names
