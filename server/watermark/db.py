"""SQLite persistence. One file, a handful of tables, no ORM.

Rules that come straight from Ring's docs and shape the schema:
- Sensor events have no history endpoint, so every webhook is persisted on
  receipt, keyed by `meta.request_id` for idempotency.
- Events can be `received` (a webhook) or `reconciled` (we noticed the state via
  `/status` because a webhook was missed). The pack reports which is which.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  account_id TEXT PRIMARY KEY,
  email TEXT,
  access_token TEXT,
  refresh_token TEXT,
  expires_at REAL,
  link_status TEXT DEFAULT 'unclaimed',
  created_at REAL,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  account_id TEXT,
  name TEXT,
  kind TEXT,                -- camera | flood_freeze | contact | temperature_humidity | air_quality | chime | unknown
  room TEXT,
  route_id TEXT,            -- rover route that reaches this sensor's room
  covered_by TEXT,          -- camera device id that already sees this room (fixed cam), if any
  chime_audio_ref TEXT,
  last_status TEXT,         -- JSON
  online INTEGER,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS events (
  request_id TEXT PRIMARY KEY,
  event_id TEXT,
  type TEXT,
  device_id TEXT,
  account_id TEXT,
  timestamp_ms INTEGER,
  received_at REAL,
  source TEXT,              -- received | reconciled | synthetic
  raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_device ON events(device_id, timestamp_ms);
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY,
  account_id TEXT,
  sensor_device_id TEXT,
  room TEXT,
  kind TEXT,                -- flood | freeze
  status TEXT,              -- open | closed
  opened_at_ms INTEGER,
  opened_source TEXT,
  closed_at_ms INTEGER,
  closed_source TEXT,
  camera_device_id TEXT,
  camera_role TEXT,         -- fixed | rover
  rover_dispatched_at_ms INTEGER,
  rover_on_station_at_ms INTEGER,
  rover_stop_reason TEXT,
  chime_status TEXT,
  notes TEXT                -- JSON
);
CREATE TABLE IF NOT EXISTS frames (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  device_id TEXT,
  session_no INTEGER,
  requested_ms INTEGER,
  media_ms INTEGER,
  origin TEXT,              -- live | recording | snapshot | mock
  drift_ms INTEGER,
  path TEXT,
  caption TEXT,
  caption_model TEXT,
  water_visible INTEGER,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_frames_incident ON frames(incident_id, media_ms);
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  device_id TEXT,
  source TEXT,              -- ring | wand
  ts_ms INTEGER,
  temperature REAL,
  humidity REAL,
  water_raw INTEGER
);
CREATE TABLE IF NOT EXISTS device_health (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  device_id TEXT,
  ts_ms INTEGER,
  online INTEGER,
  source TEXT               -- webhook | status
);
CREATE TABLE IF NOT EXISTS rover_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  ts_ms INTEGER,
  kind TEXT,                -- dispatched | ack | on_station | blocked | wet | telemetry | error | returned
  message TEXT,
  data TEXT                 -- JSON
);
CREATE TABLE IF NOT EXISTS capture_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  device_id TEXT,
  session_no INTEGER,
  started_ms INTEGER,
  ended_ms INTEGER,
  frames INTEGER,
  outcome TEXT,             -- ok | no_camera | media_not_found | error | skipped_offline
  detail TEXT
);
CREATE TABLE IF NOT EXISTS routes (
  id TEXT PRIMARY KEY,
  name TEXT,
  description TEXT,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS packs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT,
  created_at REAL,
  html_path TEXT,
  json_path TEXT,
  pdf_path TEXT,
  questions_answered INTEGER,
  questions_total INTEGER
);
"""


def now_ms() -> int:
    return int(time.time() * 1000)


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock:
            self._conn.executescript(SCHEMA)

    # ---- generic ----

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- accounts ----

    def upsert_account(self, account_id: str, **fields: Any) -> None:
        cols = {k: v for k, v in fields.items() if v is not None}
        cols["updated_at"] = time.time()
        existing = self.one("SELECT account_id FROM accounts WHERE account_id=?", (account_id,))
        if existing:
            sets = ", ".join(f"{k}=:{k}" for k in cols)
            self.execute(f"UPDATE accounts SET {sets} WHERE account_id=:account_id", {**cols, "account_id": account_id})
        else:
            cols["account_id"] = account_id
            cols["created_at"] = time.time()
            keys = ", ".join(cols)
            vals = ", ".join(f":{k}" for k in cols)
            self.execute(f"INSERT INTO accounts ({keys}) VALUES ({vals})", cols)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM accounts WHERE account_id=?", (account_id,))

    def list_accounts(self, link_status: str | None = None) -> list[dict[str, Any]]:
        if link_status:
            return self.query("SELECT * FROM accounts WHERE link_status=?", (link_status,))
        return self.query("SELECT * FROM accounts")

    def delete_account(self, account_id: str) -> dict[str, int]:
        """Content policy: delete everything, including derived data. Returns counts."""
        counts: dict[str, int] = {}
        inc_ids = [r["id"] for r in self.query("SELECT id FROM incidents WHERE account_id=?", (account_id,))]
        for table in ("frames", "readings", "device_health", "rover_log", "capture_attempts", "packs"):
            n = 0
            for iid in inc_ids:
                n += self.execute(f"DELETE FROM {table} WHERE incident_id=?", (iid,)).rowcount
            counts[table] = n
        counts["incidents"] = self.execute("DELETE FROM incidents WHERE account_id=?", (account_id,)).rowcount
        counts["events"] = self.execute("DELETE FROM events WHERE account_id=?", (account_id,)).rowcount
        counts["devices"] = self.execute("DELETE FROM devices WHERE account_id=?", (account_id,)).rowcount
        counts["accounts"] = self.execute("DELETE FROM accounts WHERE account_id=?", (account_id,)).rowcount
        return counts

    # ---- devices ----

    def upsert_device(self, device_id: str, **fields: Any) -> None:
        cols = {k: v for k, v in fields.items() if v is not None}
        if "last_status" in cols and not isinstance(cols["last_status"], str):
            cols["last_status"] = json.dumps(cols["last_status"])
        cols["updated_at"] = time.time()
        if self.one("SELECT device_id FROM devices WHERE device_id=?", (device_id,)):
            sets = ", ".join(f"{k}=:{k}" for k in cols)
            self.execute(f"UPDATE devices SET {sets} WHERE device_id=:device_id", {**cols, "device_id": device_id})
        else:
            cols["device_id"] = device_id
            keys = ", ".join(cols)
            vals = ", ".join(f":{k}" for k in cols)
            self.execute(f"INSERT INTO devices ({keys}) VALUES ({vals})", cols)

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM devices WHERE device_id=?", (device_id,))

    def list_devices(self, account_id: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        sql, params = "SELECT * FROM devices WHERE 1=1", []
        if account_id:
            sql += " AND account_id=?"
            params.append(account_id)
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        return self.query(sql + " ORDER BY name", tuple(params))

    # ---- events ----

    def insert_event(self, request_id: str, *, event_id: str | None, type: str, device_id: str | None,
                     account_id: str | None, timestamp_ms: int | None, source: str, raw: dict | str) -> bool:
        """Returns False when the request_id was already stored (a retry or a duplicate)."""
        raw_s = raw if isinstance(raw, str) else json.dumps(raw)
        try:
            self.execute(
                "INSERT INTO events (request_id, event_id, type, device_id, account_id, timestamp_ms, received_at, source, raw)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (request_id, event_id, type, device_id, account_id, timestamp_ms, time.time(), source, raw_s))
            return True
        except sqlite3.IntegrityError:
            return False

    def events_for_device(self, device_id: str, since_ms: int | None = None) -> list[dict[str, Any]]:
        if since_ms is None:
            return self.query("SELECT * FROM events WHERE device_id=? ORDER BY timestamp_ms", (device_id,))
        return self.query("SELECT * FROM events WHERE device_id=? AND timestamp_ms>=? ORDER BY timestamp_ms",
                          (device_id, since_ms))

    def events_between(self, since_ms: int, until_ms: int | None = None) -> list[dict[str, Any]]:
        until = until_ms if until_ms is not None else now_ms() + 1
        return self.query("SELECT * FROM events WHERE timestamp_ms>=? AND timestamp_ms<=? ORDER BY timestamp_ms",
                          (since_ms, until))

    # ---- incidents ----

    def insert_incident(self, row: dict[str, Any]) -> None:
        row = dict(row)
        if "notes" in row and not isinstance(row["notes"], str):
            row["notes"] = json.dumps(row["notes"])
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO incidents ({keys}) VALUES ({vals})", row)

    def update_incident(self, incident_id: str, **fields: Any) -> None:
        if not fields:
            return
        if "notes" in fields and not isinstance(fields["notes"], str):
            fields["notes"] = json.dumps(fields["notes"])
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        self.execute(f"UPDATE incidents SET {sets} WHERE id=:id", {**fields, "id": incident_id})

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM incidents WHERE id=?", (incident_id,))

    def open_incident_for_sensor(self, sensor_device_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM incidents WHERE sensor_device_id=? AND status='open' ORDER BY opened_at_ms DESC",
                        (sensor_device_id,))

    def list_incidents(self, account_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        sql, params = "SELECT * FROM incidents WHERE 1=1", []
        if account_id:
            sql += " AND account_id=?"
            params.append(account_id)
        if status:
            sql += " AND status=?"
            params.append(status)
        return self.query(sql + " ORDER BY opened_at_ms DESC", tuple(params))

    # ---- frames / readings / health / rover / captures / packs ----

    def insert_frame(self, **row: Any) -> int:
        row.setdefault("created_at", time.time())
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        cur = self.execute(f"INSERT INTO frames ({keys}) VALUES ({vals})", row)
        return int(cur.lastrowid)

    def update_frame(self, frame_id: int, **fields: Any) -> None:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        self.execute(f"UPDATE frames SET {sets} WHERE id=:id", {**fields, "id": frame_id})

    def frames_for_incident(self, incident_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM frames WHERE incident_id=? ORDER BY media_ms, id", (incident_id,))

    def get_frame(self, frame_id: int) -> dict[str, Any] | None:
        return self.one("SELECT * FROM frames WHERE id=?", (frame_id,))

    def insert_reading(self, **row: Any) -> None:
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO readings ({keys}) VALUES ({vals})", row)

    def readings_for_incident(self, incident_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM readings WHERE incident_id=? ORDER BY ts_ms", (incident_id,))

    def insert_health(self, **row: Any) -> None:
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO device_health ({keys}) VALUES ({vals})", row)

    def health_for_incident(self, incident_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM device_health WHERE incident_id=? ORDER BY ts_ms", (incident_id,))

    def insert_rover_log(self, incident_id: str, kind: str, message: str, data: dict | None = None,
                         ts_ms: int | None = None) -> None:
        self.execute("INSERT INTO rover_log (incident_id, ts_ms, kind, message, data) VALUES (?,?,?,?,?)",
                     (incident_id, ts_ms or now_ms(), kind, message, json.dumps(data or {})))

    def rover_log_for_incident(self, incident_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM rover_log WHERE incident_id=? ORDER BY ts_ms, id", (incident_id,))

    def insert_capture_attempt(self, **row: Any) -> None:
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO capture_attempts ({keys}) VALUES ({vals})", row)

    def captures_for_incident(self, incident_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM capture_attempts WHERE incident_id=? ORDER BY started_ms", (incident_id,))

    def upsert_route(self, route_id: str, name: str, description: str = "") -> None:
        self.execute("INSERT INTO routes (id, name, description, updated_at) VALUES (?,?,?,?)"
                     " ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description,"
                     " updated_at=excluded.updated_at", (route_id, name, description, time.time()))

    def list_routes(self) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM routes ORDER BY name")

    def delete_route(self, route_id: str) -> None:
        self.execute("DELETE FROM routes WHERE id=?", (route_id,))

    def insert_pack(self, **row: Any) -> int:
        row.setdefault("created_at", time.time())
        keys = ", ".join(row)
        vals = ", ".join(f":{k}" for k in row)
        cur = self.execute(f"INSERT INTO packs ({keys}) VALUES ({vals})", row)
        return int(cur.lastrowid)

    def latest_pack(self, incident_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM packs WHERE incident_id=? ORDER BY id DESC", (incident_id,))
