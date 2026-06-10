# storage/database.py
import sqlite3
from datetime import datetime
from models import WiFiNetwork, BTDevice, GPSLocation


class Database:
    def __init__(self, path: str = "civops.db"):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                wifi_count INTEGER DEFAULT 0,
                bt_count INTEGER DEFAULT 0,
                kml_path TEXT,
                gpx_path TEXT
            );
            CREATE TABLE IF NOT EXISTS wifi_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                ssid TEXT, bssid TEXT, rssi INTEGER,
                frequency INTEGER, capabilities TEXT,
                lat REAL, lon REAL, timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS bt_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                name TEXT, address TEXT, rssi INTEGER,
                device_type TEXT, manufacturer TEXT,
                lat REAL, lon REAL, timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS gps_track (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                lat REAL, lon REAL, altitude REAL,
                accuracy REAL, timestamp TEXT
            );
        """)
        self._conn.commit()

    def create_session(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (datetime.now().isoformat(),)
        )
        self._conn.commit()
        return cur.lastrowid

    def close_session(self, session_id: int, kml_path: str, gpx_path: str):
        self._conn.execute(
            "UPDATE sessions SET ended_at=?, kml_path=?, gpx_path=? WHERE id=?",
            (datetime.now().isoformat(), kml_path, gpx_path, session_id)
        )
        self._conn.commit()

    def insert_wifi(self, session_id: int, net: WiFiNetwork):
        self._conn.execute(
            "INSERT INTO wifi_detections "
            "(session_id,ssid,bssid,rssi,frequency,capabilities,lat,lon,timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (session_id, net.ssid, net.bssid, net.rssi, net.frequency,
             net.capabilities, net.lat, net.lon, net.timestamp.isoformat())
        )
        self._conn.commit()

    def insert_bt(self, session_id: int, device: BTDevice):
        self._conn.execute(
            "INSERT INTO bt_detections "
            "(session_id,name,address,rssi,device_type,manufacturer,lat,lon,timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (session_id, device.name, device.address, device.rssi, device.device_type,
             device.manufacturer, device.lat, device.lon, device.timestamp.isoformat())
        )
        self._conn.commit()

    def insert_gps(self, session_id: int, loc: GPSLocation):
        self._conn.execute(
            "INSERT INTO gps_track "
            "(session_id,lat,lon,altitude,accuracy,timestamp) VALUES (?,?,?,?,?,?)",
            (session_id, loc.lat, loc.lon, loc.altitude, loc.accuracy,
             loc.timestamp.isoformat())
        )
        self._conn.commit()

    def get_wifi_detections(self, session_id: int) -> list[WiFiNetwork]:
        rows = self._conn.execute(
            "SELECT * FROM wifi_detections WHERE session_id=?", (session_id,)
        ).fetchall()
        return [WiFiNetwork(
            ssid=r["ssid"], bssid=r["bssid"], rssi=r["rssi"],
            frequency=r["frequency"], capabilities=r["capabilities"],
            lat=r["lat"], lon=r["lon"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def get_bt_detections(self, session_id: int) -> list[BTDevice]:
        rows = self._conn.execute(
            "SELECT * FROM bt_detections WHERE session_id=?", (session_id,)
        ).fetchall()
        return [BTDevice(
            name=r["name"], address=r["address"], rssi=r["rssi"],
            device_type=r["device_type"], manufacturer=r["manufacturer"],
            lat=r["lat"], lon=r["lon"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def get_gps_track(self, session_id: int) -> list[GPSLocation]:
        rows = self._conn.execute(
            "SELECT * FROM gps_track WHERE session_id=?", (session_id,)
        ).fetchall()
        return [GPSLocation(
            lat=r["lat"], lon=r["lon"], altitude=r["altitude"],
            accuracy=r["accuracy"],
            timestamp=datetime.fromisoformat(r["timestamp"])
        ) for r in rows]

    def close(self):
        self._conn.close()
