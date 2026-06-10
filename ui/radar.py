# ui/radar.py
from textual.widget import Widget
from textual.widgets import DataTable, Label
from textual.app import ComposeResult
from models import WiFiNetwork, BTDevice, GPSLocation

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
    def compose(self) -> ComposeResult:
        yield Label("GPS: waiting for fix", id="gps-status")
        yield Label("── WiFi ───────────────────────────────────────────", markup=False)
        yield DataTable(id="wifi-table", show_cursor=False)
        yield Label("── Bluetooth ──────────────────────────────────────", markup=False)
        yield DataTable(id="bt-table", show_cursor=False)

    def on_mount(self) -> None:
        self.query_one("#wifi-table", DataTable).add_columns(
            "Signal", "SSID", "BSSID", "RSSI", "Freq", "Security", "Vendor"
        )
        self.query_one("#bt-table", DataTable).add_columns(
            "Signal", "Name", "Address", "RSSI", "Type", "Vendor"
        )

    def update_gps(self, loc: GPSLocation) -> None:
        self.query_one("#gps-status", Label).update(
            f"GPS: {loc.lat:.4f},{loc.lon:.4f} ±{loc.accuracy:.0f}m"
        )

    def refresh_tables(self, wifi: list[WiFiNetwork], bt: list[BTDevice], scan_count: int) -> None:
        self.query_one("#gps-status", Label).update(f"Scan #{scan_count} — {len(wifi)} networks")
        wifi_table = self.query_one("#wifi-table", DataTable)
        wifi_table.clear()
        for net in sorted(wifi, key=lambda n: n.rssi, reverse=True):
            color = _rssi_color(net.rssi)
            security = "⚠ OPEN" if not net.capabilities or net.capabilities == "[]" else net.capabilities[:10]
            wifi_table.add_row(
                _rssi_bar(net.rssi), net.ssid, net.bssid,
                f"[{color}]{net.rssi}[/{color}]",
                str(net.frequency), security, "",
            )
        bt_table = self.query_one("#bt-table", DataTable)
        bt_table.clear()
        for device in sorted(bt, key=lambda d: d.rssi, reverse=True):
            color = _rssi_color(device.rssi)
            bt_table.add_row(
                _rssi_bar(device.rssi), device.name, device.address,
                f"[{color}]{device.rssi}[/{color}]",
                device.device_type, device.manufacturer or "",
            )
