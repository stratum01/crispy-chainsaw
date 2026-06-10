# ui/radar.py
import asyncio
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
        self._scan_count = 0

    def compose(self) -> ComposeResult:
        yield Label("GPS: waiting for fix", id="gps-status")
        yield Label("── WiFi ───────────────────────────────────────────", markup=False)
        yield DataTable(id="wifi-table", show_cursor=False)
        yield Label("── Bluetooth ──────────────────────────────────────", markup=False)
        yield DataTable(id="bt-table", show_cursor=False)

    def on_mount(self) -> None:
        try:
            wifi_table = self.query_one("#wifi-table", DataTable)
            wifi_table.add_columns("Signal", "SSID", "BSSID", "RSSI", "Freq", "Security", "Vendor")
            bt_table = self.query_one("#bt-table", DataTable)
            bt_table.add_columns("Signal", "Name", "Address", "RSSI", "Type", "Vendor")
            self.run_worker(self._scan_loop, exclusive=True, name="scan")
            self.run_worker(self._gps_loop, exclusive=True, name="gps")
            self.notify("Radar ready", timeout=2)
        except Exception as e:
            self.notify(f"Mount error: {e}", severity="error", timeout=10)

    async def _gps_loop(self) -> None:
        while True:
            try:
                loc = await asyncio.get_running_loop().run_in_executor(None, self._gps.poll)
                if loc:
                    self.query_one("#gps-status", Label).update(
                        f"GPS: {loc.lat:.4f},{loc.lon:.4f} ±{loc.accuracy:.0f}m"
                    )
                    self._db.insert_gps(self._session_id, loc)
                    self._jsonl.log_gps(loc)
            except Exception as e:
                self.notify(f"GPS error: {e}", severity="warning", timeout=5)
            await asyncio.sleep(3.0)

    async def _scan_loop(self) -> None:
        while True:
            try:
                self._scan_count += 1
                self.query_one("#gps-status", Label).update(f"Scanning... #{self._scan_count}")
                loop = asyncio.get_running_loop()
                gps = self._gps.current_location
                wifi_events = await loop.run_in_executor(None, lambda: self._wifi.scan(gps=gps))
                bt_events = await loop.run_in_executor(None, lambda: self._bt.scan(gps=gps))
                self.query_one("#gps-status", Label).update(
                    f"Scan #{self._scan_count} — {len(wifi_events.appeared)} new wifi"
                )

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
            except Exception as e:
                self.notify(f"Scan error: {e}", severity="error", timeout=8)
            await asyncio.sleep(self._scan_interval)

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
