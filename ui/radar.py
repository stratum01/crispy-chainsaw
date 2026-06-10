# ui/radar.py
from textual.widget import Widget
from textual.widgets import DataTable, Label
from textual.app import ComposeResult
from scanners.wifi import WiFiScanner
from scanners.bluetooth import BTScanner
from scanners.gps import GPSScanner
from storage.database import Database
from storage.logger import JSONLLogger

_BAR_WIDTH = 9


def _rssi_bar(rssi: int) -> str:
    filled = max(0, min(_BAR_WIDTH, int((rssi + 100) / 100 * _BAR_WIDTH)))
    return "▓" * filled + "░" * (_BAR_WIDTH - filled)


def _rssi_color(rssi: int) -> str:
    if rssi >= -65:
        return "green"
    if rssi >= -80:
        return "yellow"
    return "red"


class RadarScreen(Widget):
    def __init__(
        self,
        wifi_scanner: WiFiScanner,
        bt_scanner: BTScanner,
        gps_scanner: GPSScanner,
        db: Database,
        logger: JSONLLogger,
        session_id: int,
        scan_interval: float,
    ):
        super().__init__()
        self._wifi = wifi_scanner
        self._bt = bt_scanner
        self._gps = gps_scanner
        self._db = db
        self._jsonl = logger
        self._session_id = session_id
        self._scan_interval = scan_interval

    def compose(self) -> ComposeResult:
        yield Label("GPS: waiting for fix", id="gps-status")
        yield Label("── WiFi ───────────────────────────────────────────", markup=False)
        yield DataTable(id="wifi-table", show_cursor=False)
        yield Label("── Bluetooth ──────────────────────────────────────", markup=False)
        yield DataTable(id="bt-table", show_cursor=False)

    def on_mount(self) -> None:
        wifi_table = self.query_one("#wifi-table", DataTable)
        wifi_table.add_columns("Signal", "SSID", "BSSID", "RSSI", "Freq", "Security", "Vendor")
        bt_table = self.query_one("#bt-table", DataTable)
        bt_table.add_columns("Signal", "Name", "Address", "RSSI", "Type", "Vendor")
        self.set_interval(self._scan_interval, self._do_scan)
        self.set_interval(3.0, self._do_gps_poll)

    def _do_gps_poll(self) -> None:
        loc = self._gps.poll()
        if loc:
            self.query_one("#gps-status", Label).update(
                f"GPS: {loc.lat:.4f},{loc.lon:.4f} ±{loc.accuracy:.0f}m"
            )
            self._db.insert_gps(self._session_id, loc)
            self._jsonl.log_gps(loc)

    def _do_scan(self) -> None:
        gps = self._gps.current_location
        wifi_events = self._wifi.scan(gps=gps)
        bt_events = self._bt.scan(gps=gps)

        for net in wifi_events.appeared:
            self._db.insert_wifi(self._session_id, net)
            self._jsonl.log_wifi(net)
            self.app.add_log_event(
                f"[+WIFI] {net.ssid} {net.bssid} {net.rssi}dBm {net.capabilities[:8]}"
            )

        for net in wifi_events.disappeared:
            self.app.add_log_event(f"[-WIFI] {net.ssid} last seen {net.rssi}dBm")

        for net in wifi_events.updated:
            self.app.add_log_event(f"[RSSI] {net.ssid} → {net.rssi}dBm")

        for device in bt_events.appeared:
            self._db.insert_bt(self._session_id, device)
            self._jsonl.log_bt(device)
            tag = "BLE" if device.device_type == "BLE" else "BT"
            self.app.add_log_event(
                f"[+{tag}] {device.name} {device.address} {device.rssi}dBm"
            )

        for device in bt_events.disappeared:
            self.app.add_log_event(f"[-BT] {device.name} last seen {device.rssi}dBm")

        self._refresh_tables()

    def _refresh_tables(self) -> None:
        wifi_table = self.query_one("#wifi-table", DataTable)
        wifi_table.clear()
        for net in sorted(self._wifi.current, key=lambda n: n.rssi, reverse=True):
            color = _rssi_color(net.rssi)
            security = "⚠ OPEN" if not net.capabilities or net.capabilities == "[]" else net.capabilities[:10]
            wifi_table.add_row(
                _rssi_bar(net.rssi), net.ssid, net.bssid,
                f"[{color}]{net.rssi}[/{color}]",
                str(net.frequency), security, "",
            )
        bt_table = self.query_one("#bt-table", DataTable)
        bt_table.clear()
        for device in sorted(self._bt.current, key=lambda d: d.rssi, reverse=True):
            color = _rssi_color(device.rssi)
            bt_table.add_row(
                _rssi_bar(device.rssi), device.name, device.address,
                f"[{color}]{device.rssi}[/{color}]",
                device.device_type, device.manufacturer or "",
            )
