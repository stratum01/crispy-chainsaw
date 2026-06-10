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
        self._logger = logger
        self._session_id = session_id
        self._scan_interval = scan_interval
        self._wifi_scanner = WiFiScanner(backend)
        self._bt_scanner = BTScanner(backend)
        self._gps_scanner = GPSScanner(backend)

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="radar"):
            with TabPane("RADAR", id="radar"):
                yield RadarScreen(
                    self._wifi_scanner, self._bt_scanner, self._gps_scanner,
                    self._db, self._logger, self._session_id, self._scan_interval,
                )
            with TabPane("LOG", id="log"):
                yield LogScreen()
            with TabPane("MAP", id="map"):
                yield MapScreen(self._db, self._session_id)
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def add_log_event(self, text: str) -> None:
        try:
            self.query_one(LogScreen).add_event(text)
        except Exception:
            pass
