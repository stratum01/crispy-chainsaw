# ui/map_view.py
from datetime import datetime
from pathlib import Path
from textual.widget import Widget
from textual.widgets import Static, Label
from textual.app import ComposeResult
from textual.binding import Binding
from storage.database import Database
from export.kml import export_kml
from export.gpx import export_gpx

_MAP_WIDTH = 42
_MAP_HEIGHT = 14


def _render_ascii_track(track, wifi, bt, width=_MAP_WIDTH, height=_MAP_HEIGHT) -> str:
    if not track:
        return "  (no GPS track yet — waiting for fix)"

    lats = [p.lat for p in track]
    lons = [p.lon for p in track]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    lat_range = lat_max - lat_min or 0.001
    lon_range = lon_max - lon_min or 0.001

    grid = [[" " for _ in range(width)] for _ in range(height)]

    def to_xy(lat, lon):
        x = int((lon - lon_min) / lon_range * (width - 1))
        y = int((lat_max - lat) / lat_range * (height - 1))
        return max(0, min(width - 1, x)), max(0, min(height - 1, y))

    for loc in track:
        x, y = to_xy(loc.lat, loc.lon)
        grid[y][x] = "·"

    x, y = to_xy(track[0].lat, track[0].lon)
    grid[y][x] = "★"

    for net in wifi:
        if net.lat and net.lon:
            x, y = to_xy(net.lat, net.lon)
            grid[y][x] = "W"

    for device in bt:
        if device.lat and device.lon:
            x, y = to_xy(device.lat, device.lon)
            grid[y][x] = "B"

    legend = "  · path  ★ start  W wifi  B bt"
    return "\n".join("  " + "".join(row) for row in grid) + "\n" + legend


class MapScreen(Widget):
    BINDINGS = [
        Binding("k", "export_kml", "KML"),
        Binding("g", "export_gpx", "GPX"),
    ]

    def __init__(self, db: Database, session_id: int):
        super().__init__()
        self._db = db
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        yield Static("", id="ascii-map")
        yield Static("", id="session-summary")
        yield Label("", id="export-status")

    def on_mount(self) -> None:
        self.set_interval(5.0, self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        self.query_one("#ascii-map", Static).update(_render_ascii_track(track, wifi, bt))
        open_count = sum(
            1 for n in wifi if not n.capabilities or n.capabilities == "[]"
        )
        self.query_one("#session-summary", Static).update(
            f"WiFi: {len(wifi)}  BT/BLE: {len(bt)}  GPS fixes: {len(track)}"
            + (f"  ⚠ {open_count} open" if open_count else "")
        )

    def _output_path(self, ext: str) -> str:
        base = Path.home() / "civops-data"
        base.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d-%H-%M")
        return str(base / f"civops-{ts}.{ext}")

    def action_export_kml(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        path = self._output_path("kml")
        export_kml(wifi=wifi, bt=bt, track=track, path=path)
        self.query_one("#export-status", Label).update(f"KML saved: {path}")
        self.app.add_log_event(f"[EXPORT] KML → {path}")

    def action_export_gpx(self) -> None:
        track = self._db.get_gps_track(self._session_id)
        wifi = self._db.get_wifi_detections(self._session_id)
        bt = self._db.get_bt_detections(self._session_id)
        path = self._output_path("gpx")
        export_gpx(wifi=wifi, bt=bt, track=track, path=path)
        self.query_one("#export-status", Label).update(f"GPX saved: {path}")
        self.app.add_log_event(f"[EXPORT] GPX → {path}")
