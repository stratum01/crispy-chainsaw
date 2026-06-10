# ui/radar.py
from textual.widget import Widget
from textual.widgets import Static, Label
from textual.app import ComposeResult
from models import WiFiNetwork, BTDevice, GPSLocation

_BAR_WIDTH = 9


def _rssi_bar(rssi: int) -> str:
    filled = max(0, min(_BAR_WIDTH, int((rssi + 100) / 100 * _BAR_WIDTH)))
    return "▓" * filled + "░" * (_BAR_WIDTH - filled)


class RadarScreen(Widget):
    def compose(self) -> ComposeResult:
        yield Label("GPS: waiting for fix", id="gps-status")
        yield Static("── WiFi ─────────────────────────────────", id="wifi-display")
        yield Static("── Bluetooth ────────────────────────────", id="bt-display")

    def update_gps(self, loc: GPSLocation) -> None:
        self.query_one("#gps-status", Label).update(
            f"GPS: {loc.lat:.4f},{loc.lon:.4f} ±{loc.accuracy:.0f}m"
        )

    def refresh_tables(self, wifi: list[WiFiNetwork], bt: list[BTDevice], scan_count: int) -> None:
        self.query_one("#gps-status", Label).update(
            f"Scan #{scan_count} — {len(wifi)} networks"
        )

        if wifi:
            lines = ["── WiFi ─────────────────────────────────"]
            for net in sorted(wifi, key=lambda n: n.rssi, reverse=True):
                security = "OPEN" if not net.capabilities or net.capabilities == "[]" else net.capabilities[:8]
                lines.append(f"{_rssi_bar(net.rssi)} {net.rssi:4}  {net.ssid or '(hidden)'}  {security}")
            self.query_one("#wifi-display", Static).update("\n".join(lines))
        else:
            self.query_one("#wifi-display", Static).update("── WiFi ─── no networks ─────────────────")

        if bt:
            lines = ["── Bluetooth ────────────────────────────"]
            for device in sorted(bt, key=lambda d: d.rssi, reverse=True):
                lines.append(f"{_rssi_bar(device.rssi)} {device.rssi:4}  {device.name}  {device.device_type}")
            self.query_one("#bt-display", Static).update("\n".join(lines))
        else:
            self.query_one("#bt-display", Static).update("── Bluetooth ─── no devices ─────────────")
