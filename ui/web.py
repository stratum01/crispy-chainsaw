# ui/web.py
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from scanners.wifi import WiFiScanner
from scanners.bluetooth import BTScanner
from scanners.gps import GPSScanner
from storage.database import Database
from storage.logger import JSONLLogger
from backends.base import BaseBackend

_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CIVOPS Recon Radar</title>
<style>
  body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:12px; margin:0; }
  h2 { color:#58a6ff; margin:0 0 4px; font-size:16px; }
  .status { color:#8b949e; font-size:12px; margin-bottom:12px; }
  table { width:100%; border-collapse:collapse; font-size:12px; margin-bottom:16px; }
  th { color:#8b949e; text-align:left; padding:4px 6px; border-bottom:1px solid #21262d; }
  td { padding:4px 6px; border-bottom:1px solid #161b22; white-space:nowrap; }
  .bar { color:#3fb950; letter-spacing:-1px; }
  .strong { color:#3fb950; }
  .medium { color:#ffa657; }
  .weak   { color:#f85149; }
  .open   { color:#f85149; }
  #log { height:160px; overflow-y:auto; font-size:11px; background:#161b22;
         padding:8px; border-radius:4px; }
  .log-wifi { color:#3fb950; }
  .log-bt   { color:#58a6ff; }
  .log-gps  { color:#8b949e; }
  #gps-bar  { color:#8b949e; font-size:12px; margin-bottom:12px; }
</style>
</head>
<body>
<h2>CIVOPS Recon Radar</h2>
<div id="gps-bar">GPS: waiting for fix</div>
<h2>WiFi</h2>
<div id="wifi-div"><table><thead><tr>
  <th>Signal</th><th>SSID</th><th>RSSI</th><th>Security</th>
</tr></thead><tbody id="wifi-body"></tbody></table></div>
<h2>Bluetooth</h2>
<div id="bt-div"><table><thead><tr>
  <th>Signal</th><th>Name</th><th>RSSI</th><th>Type</th><th>Vendor</th>
</tr></thead><tbody id="bt-body"></tbody></table></div>
<h2>Log</h2>
<div id="log"></div>
<div class="status" id="last-update">Connecting...</div>
<script>
function bar(rssi) {
  let n = Math.max(0, Math.min(9, Math.round((rssi + 100) / 100 * 9)));
  return '▓'.repeat(n) + '░'.repeat(9 - n);
}
function cls(rssi) {
  return rssi >= -65 ? 'strong' : rssi >= -80 ? 'medium' : 'weak';
}
function refresh() {
  fetch('/api/data').then(r => r.json()).then(d => {
    document.getElementById('gps-bar').textContent =
      d.gps ? 'GPS: ' + d.gps.lat.toFixed(4) + ',' + d.gps.lon.toFixed(4) +
               ' ±' + Math.round(d.gps.accuracy) + 'm' : 'GPS: waiting for fix';

    let wb = document.getElementById('wifi-body');
    wb.innerHTML = d.wifi.map(n => {
      let c = cls(n.rssi);
      let sec = n.capabilities ? n.capabilities.slice(0,10) : 'OPEN';
      let secClass = sec === 'OPEN' ? ' class="open"' : '';
      return '<tr><td class="bar">' + bar(n.rssi) + '</td>' +
             '<td>' + (n.ssid || '(hidden)') + '</td>' +
             '<td class="' + c + '">' + n.rssi + '</td>' +
             '<td' + secClass + '>' + sec + '</td></tr>';
    }).join('');

    let bb = document.getElementById('bt-body');
    bb.innerHTML = d.bt.map(dev => {
      let c = cls(dev.rssi);
      return '<tr><td class="bar">' + bar(dev.rssi) + '</td>' +
             '<td>' + dev.name + '</td>' +
             '<td class="' + c + '">' + dev.rssi + '</td>' +
             '<td>' + dev.device_type + '</td>' +
             '<td>' + (dev.manufacturer || '') + '</td></tr>';
    }).join('');

    let log = document.getElementById('log');
    log.innerHTML = d.events.slice().reverse().map(e => {
      let cls2 = e.includes('WIFI') ? 'log-wifi' : e.includes('BT') || e.includes('BLE') ? 'log-bt' : 'log-gps';
      return '<div class="' + cls2 + '">' + e + '</div>';
    }).join('');

    document.getElementById('last-update').textContent =
      'Last update: ' + new Date().toLocaleTimeString() +
      ' — ' + d.wifi.length + ' WiFi, ' + d.bt.length + ' BT';
  }).catch(() => {
    document.getElementById('last-update').textContent = 'Reconnecting...';
  });
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


class WebUI:
    def __init__(
        self,
        backend: BaseBackend,
        db: Database,
        logger: JSONLLogger,
        session_id: int,
        scan_interval: float = 5.0,
    ):
        self._wifi_scanner = WiFiScanner(backend)
        self._bt_scanner = BTScanner(backend)
        self._gps_scanner = GPSScanner(backend)
        self._db = db
        self._jsonl = logger
        self._session_id = session_id
        self._scan_interval = scan_interval
        self._events: list[str] = []
        self._lock = threading.Lock()

        self._flask = Flask(__name__)
        self._flask.add_url_rule("/", "index", self._index)
        self._flask.add_url_rule("/api/data", "data", self._api_data)

    def _index(self):
        return render_template_string(_HTML)

    def _api_data(self):
        with self._lock:
            gps = self._gps_scanner.current_location
            wifi = self._wifi_scanner.current
            bt = self._bt_scanner.current
            events = list(self._events[-100:])
        return jsonify({
            "wifi": [
                {"ssid": n.ssid, "bssid": n.bssid, "rssi": n.rssi,
                 "capabilities": n.capabilities}
                for n in sorted(wifi, key=lambda n: n.rssi, reverse=True)
            ],
            "bt": [
                {"name": d.name, "address": d.address, "rssi": d.rssi,
                 "device_type": d.device_type, "manufacturer": d.manufacturer}
                for d in sorted(bt, key=lambda d: d.rssi, reverse=True)
            ],
            "gps": {"lat": gps.lat, "lon": gps.lon, "accuracy": gps.accuracy}
                   if gps else None,
            "events": events,
        })

    def _scan_loop(self):
        while True:
            try:
                gps = self._gps_scanner.poll()
                wifi_events = self._wifi_scanner.scan(gps=gps)
                bt_events = self._bt_scanner.scan(gps=gps)
                ts = datetime.now().strftime("%H:%M:%S")
                with self._lock:
                    for net in wifi_events.appeared:
                        self._db.insert_wifi(self._session_id, net)
                        self._jsonl.log_wifi(net)
                        self._events.append(
                            f"{ts} [+WIFI] {net.ssid} {net.bssid} {net.rssi}dBm"
                        )
                    for net in wifi_events.disappeared:
                        self._events.append(f"{ts} [-WIFI] {net.ssid}")
                    for net in wifi_events.updated:
                        self._events.append(f"{ts} [RSSI] {net.ssid} → {net.rssi}dBm")
                    for dev in bt_events.appeared:
                        self._db.insert_bt(self._session_id, dev)
                        self._jsonl.log_bt(dev)
                        tag = "BLE" if dev.device_type == "BLE" else "BT"
                        self._events.append(
                            f"{ts} [+{tag}] {dev.name} {dev.address} {dev.rssi}dBm"
                        )
                    for dev in bt_events.disappeared:
                        self._events.append(f"{ts} [-BT] {dev.name}")
                    if gps:
                        self._db.insert_gps(self._session_id, gps)
                        self._jsonl.log_gps(gps)
                        self._events.append(
                            f"{ts} [GPS] {gps.lat:.4f},{gps.lon:.4f} ±{gps.accuracy:.0f}m"
                        )
            except Exception as e:
                with self._lock:
                    self._events.append(f"[ERROR] {e}")
            time.sleep(self._scan_interval)

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        t = threading.Thread(target=self._scan_loop, daemon=True)
        t.start()
        print(f"\n  CIVOPS Recon Radar running at http://localhost:{port}\n")
        self._flask.run(host=host, port=port, debug=False, use_reloader=False)
