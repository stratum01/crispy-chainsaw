import xml.etree.ElementTree as ET
from models import WiFiNetwork, BTDevice, GPSLocation

_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", _NS)


def export_kml(
    wifi: list[WiFiNetwork],
    bt: list[BTDevice],
    track: list[GPSLocation],
    path: str,
):
    kml = ET.Element(f"{{{_NS}}}kml")
    doc = ET.SubElement(kml, f"{{{_NS}}}Document")

    for net in wifi:
        if net.lat is None or net.lon is None:
            continue
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = net.ssid
        ET.SubElement(pm, f"{{{_NS}}}description").text = (
            f"BSSID: {net.bssid}\nRSSI: {net.rssi}dBm\nSecurity: {net.capabilities}"
        )
        pt = ET.SubElement(pm, f"{{{_NS}}}Point")
        ET.SubElement(pt, f"{{{_NS}}}coordinates").text = f"{net.lon},{net.lat},0"

    for device in bt:
        if device.lat is None or device.lon is None:
            continue
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = device.name
        ET.SubElement(pm, f"{{{_NS}}}description").text = (
            f"Address: {device.address}\nRSSI: {device.rssi}dBm\n"
            f"Type: {device.device_type}\nVendor: {device.manufacturer or 'unknown'}"
        )
        pt = ET.SubElement(pm, f"{{{_NS}}}Point")
        ET.SubElement(pt, f"{{{_NS}}}coordinates").text = f"{device.lon},{device.lat},0"

    if track:
        pm = ET.SubElement(doc, f"{{{_NS}}}Placemark")
        ET.SubElement(pm, f"{{{_NS}}}name").text = "GPS Track"
        ls = ET.SubElement(pm, f"{{{_NS}}}LineString")
        ET.SubElement(ls, f"{{{_NS}}}coordinates").text = " ".join(
            f"{loc.lon},{loc.lat},{loc.altitude}" for loc in track
        )

    tree = ET.ElementTree(kml)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)
