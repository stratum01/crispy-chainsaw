# ui/app.py
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, Footer
from backends.base import BaseBackend
from storage.database import Database
from storage.logger import JSONLLogger
from scanners.wifi import WiFiScanner
from scanners.bluetooth import BTScanner
from scanners.gps import GPSScanner
from ui.radar import RadarScreen
from ui.log_view import LogScreen
from ui.map_view import MapScreen


class CivopsApp(App):
    CSS = "TabbedContent { height: 1fr; }"

    BINDINGS = [
        ("r", "switch_tab('radar')", "Radar"),
        ("l", "switch_tab('log')", "Log"),
        ("m", "switch_tab('map')", "Map"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        backend: BaseBackend,
        db: Database,
        logger: JSONLLogger,
        session_id: int,
        scan_interval: float = 5.0,
    ):
        super().__init__()
        self._backend = backend
        self._db = db
        self._jsonl = logger
        self._session_id = session_id
        self._scan_interval = scan_interval
        self._wifi_scanner = WiFiScanner(backend)
        self._bt_scanner = BTScanner(backend)
        self._gps_scanner = GPSScanner(backend)
        self._scan_count = 0

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="radar"):
            with TabPane("RADAR", id="radar"):
                yield RadarScreen()
            with TabPane("LOG", id="log"):
                yield LogScreen()
            with TabPane("MAP", id="map"):
                yield MapScreen(self._db, self._session_id)
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self._scan_interval, self._do_scan)
        self.set_interval(3.0, self._do_gps_poll)
        self.notify("App ready — scanning started", timeout=3)

    def _do_gps_poll(self) -> None:
        try:
            loc = self._gps_scanner.poll()
            if loc:
                self._db.insert_gps(self._session_id, loc)
                self._jsonl.log_gps(loc)
                try:
                    self.query_one(RadarScreen).update_gps(loc)
                except Exception:
                    pass
        except Exception as e:
            self.notify(f"GPS error: {e}", severity="warning", timeout=5)

    def _do_scan(self) -> None:
        try:
            self._scan_count += 1
            gps = self._gps_scanner.current_location
            wifi_events = self._wifi_scanner.scan(gps=gps)
            bt_events = self._bt_scanner.scan(gps=gps)

            for net in wifi_events.appeared:
                self._db.insert_wifi(self._session_id, net)
                self._jsonl.log_wifi(net)
                self.add_log_event(
                    f"[+WIFI] {net.ssid} {net.bssid} {net.rssi}dBm {net.capabilities[:8]}"
                )
            for net in wifi_events.disappeared:
                self.add_log_event(f"[-WIFI] {net.ssid} last seen {net.rssi}dBm")
            for net in wifi_events.updated:
                self.add_log_event(f"[RSSI] {net.ssid} → {net.rssi}dBm")
            for device in bt_events.appeared:
                self._db.insert_bt(self._session_id, device)
                self._jsonl.log_bt(device)
                tag = "BLE" if device.device_type == "BLE" else "BT"
                self.add_log_event(
                    f"[+{tag}] {device.name} {device.address} {device.rssi}dBm"
                )
            for device in bt_events.disappeared:
                self.add_log_event(f"[-BT] {device.name} last seen {device.rssi}dBm")

            try:
                self.query_one(RadarScreen).refresh_tables(
                    self._wifi_scanner.current,
                    self._bt_scanner.current,
                    self._scan_count,
                )
            except Exception:
                pass
        except Exception as e:
            self.notify(f"Scan error: {e}", severity="error", timeout=8)

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def add_log_event(self, text: str) -> None:
        try:
            self.query_one(LogScreen).add_event(text)
        except Exception:
            pass
