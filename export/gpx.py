import xml.etree.ElementTree as ET
from models import WiFiNetwork, BTDevice, GPSLocation

_NS = "http://www.topografix.com/GPX/1/1"
ET.register_namespace("", _NS)


def export_gpx(
    wifi: list[WiFiNetwork],
    bt: list[BTDevice],
    track: list[GPSLocation],
    path: str,
):
    gpx = ET.Element(f"{{{_NS}}}gpx", version="1.1", creator="civops")

    for net in wifi:
        if net.lat is None or net.lon is None:
            continue
        wpt = ET.SubElement(gpx, f"{{{_NS}}}wpt", lat=str(net.lat), lon=str(net.lon))
        ET.SubElement(wpt, f"{{{_NS}}}name").text = net.ssid
        ET.SubElement(wpt, f"{{{_NS}}}desc").text = (
            f"BSSID:{net.bssid} RSSI:{net.rssi}dBm Security:{net.capabilities}"
        )

    for device in bt:
        if device.lat is None or device.lon is None:
            continue
        wpt = ET.SubElement(gpx, f"{{{_NS}}}wpt", lat=str(device.lat), lon=str(device.lon))
        ET.SubElement(wpt, f"{{{_NS}}}name").text = device.name
        ET.SubElement(wpt, f"{{{_NS}}}desc").text = (
            f"Address:{device.address} RSSI:{device.rssi}dBm Type:{device.device_type}"
        )

    if track:
        trk = ET.SubElement(gpx, f"{{{_NS}}}trk")
        ET.SubElement(trk, f"{{{_NS}}}name").text = "CIVOPS Track"
        seg = ET.SubElement(trk, f"{{{_NS}}}trkseg")
        for loc in track:
            trkpt = ET.SubElement(seg, f"{{{_NS}}}trkpt", lat=str(loc.lat), lon=str(loc.lon))
            ET.SubElement(trkpt, f"{{{_NS}}}ele").text = str(loc.altitude)
            ET.SubElement(trkpt, f"{{{_NS}}}time").text = loc.timestamp.isoformat()

    tree = ET.ElementTree(gpx)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)
