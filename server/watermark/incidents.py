"""The incident state machine.

    flood_detected  ──► open ──► (chime) ──► (dispatch rover) ──► capture loop ──► ...
    flood_cleared   ──► close ──► build pack

Two things are deliberate:
- Persist first. The webhook row goes in before anything else because Ring
  keeps no history for sensor events; if the process dies after this line the
  event still exists.
- Reconcile against `/status`. A missed webhook must not silently end a capture
  or leave a flood unrecorded, so the loop and a background task both re-read
  the sensor's `flood_detection.faulted` and act on it, marking the resulting
  events `reconciled` so the pack can say which came from Ring and which from
  polling.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from ringpartner import RingClient, WebhookEvent, make_event

from . import chime as chime_mod
from .blobs import BlobStore
from .capture import CaptureBackend, Frame
from .captions import Captioner
from .config import Settings
from .db import Database, now_ms
from .dispatch import Command, Dispatcher
from .ring import RingService

log = logging.getLogger("watermark.incidents")

OPEN_EVENTS = {"flood_detected": "flood", "freeze_detected": "freeze"}
CLOSE_EVENTS = {"flood_cleared": "flood", "freeze_cleared": "freeze"}
READING_EVENTS = {"temperature_exceeded", "temperature_cleared", "humidity_exceeded", "humidity_cleared"}


class IncidentManager:
    def __init__(self, settings: Settings, db: Database, ring: RingService, capture: CaptureBackend,
                 captioner: Captioner, dispatcher: Dispatcher, blobs: BlobStore, pack_builder) -> None:
        self.settings = settings
        self.db = db
        self.ring = ring
        self.capture = capture
        self.captioner = captioner
        self.dispatcher = dispatcher
        self.blobs = blobs
        self.pack_builder = pack_builder
        self._tasks: dict[str, asyncio.Task] = {}
        self._rover_ready: dict[str, asyncio.Event] = {}
        self._closing: set[str] = set()

    # ------------------------------------------------------------------ events

    async def handle_event(self, ev: WebhookEvent, source: str = "received") -> dict[str, Any]:
        inserted = self.db.insert_event(ev.request_id, event_id=ev.event_id, type=ev.type, device_id=ev.device_id,
                                        account_id=ev.account_id, timestamp_ms=ev.timestamp_ms, source=source,
                                        raw=ev.raw)
        if not inserted:
            return {"status": "duplicate", "request_id": ev.request_id}

        if ev.type in OPEN_EVENTS:
            inc = await self.open_incident(ev, source)
            return {"status": "opened", "incident_id": inc["id"] if inc else None}
        if ev.type in CLOSE_EVENTS:
            inc = self.db.open_incident_for_sensor(ev.device_id or "")
            if inc:
                await self.close_incident(inc["id"], ev.timestamp_ms or now_ms(), source)
                return {"status": "closed", "incident_id": inc["id"]}
            return {"status": "ignored", "reason": "no open incident for sensor"}
        if ev.type in ("device_online", "device_offline"):
            online = ev.type == "device_online"
            if ev.device_id:
                self.db.upsert_device(ev.device_id, online=int(online), account_id=ev.account_id)
                for inc in self._open_incidents_using(ev.device_id):
                    self.db.insert_health(incident_id=inc["id"], device_id=ev.device_id,
                                          ts_ms=ev.timestamp_ms or now_ms(), online=int(online), source="webhook")
            return {"status": "health"}
        if ev.type in READING_EVENTS and ev.reading is not None:
            for inc in self.db.list_incidents(account_id=ev.account_id, status="open"):
                self.db.insert_reading(incident_id=inc["id"], device_id=ev.device_id, source="ring",
                                       ts_ms=ev.timestamp_ms or now_ms(),
                                       temperature=ev.reading if ev.type.startswith("temperature") else None,
                                       humidity=ev.reading if ev.type.startswith("humidity") else None,
                                       water_raw=None)
            return {"status": "reading"}
        if ev.type == "device_added" and ev.account_id:
            try:
                await asyncio.to_thread(self.ring.discover, ev.account_id)
            except Exception as e:  # noqa: BLE001
                log.warning("discover after device_added failed: %s", e)
            return {"status": "discovered"}
        if ev.type == "app_integration_removed" and ev.account_id:
            # Tokens are revoked by Ring at this point. Data deletion is the user's
            # explicit action in the app (content policy), so only mark the link.
            self.db.upsert_account(ev.account_id, link_status="removed")
            return {"status": "unlinked"}
        if ev.type == "subscription_deactivated" and ev.account_id:
            self.db.upsert_account(ev.account_id, link_status="subscription_inactive")
            return {"status": "subscription_inactive"}
        return {"status": "stored"}

    def _open_incidents_using(self, device_id: str) -> list[dict[str, Any]]:
        return [i for i in self.db.list_incidents(status="open")
                if device_id in (i.get("sensor_device_id"), i.get("camera_device_id"))]

    # ---------------------------------------------------------------- open

    async def open_incident(self, ev: WebhookEvent, source: str) -> dict[str, Any] | None:
        if not ev.device_id:
            return None
        existing = self.db.open_incident_for_sensor(ev.device_id)
        if existing:
            return existing
        sensor = self.db.get_device(ev.device_id)
        if sensor is None and ev.account_id:
            try:
                await asyncio.to_thread(self.ring.discover, ev.account_id)
            except Exception as e:  # noqa: BLE001
                log.warning("discover failed: %s", e)
            sensor = self.db.get_device(ev.device_id) or {}
        sensor = sensor or {}
        account_id = ev.account_id or sensor.get("account_id") or ""
        kind = OPEN_EVENTS[ev.type]
        room = sensor.get("room") or sensor.get("name") or "unnamed room"

        camera_id, role = self._pick_camera(sensor, account_id)
        incident_id = f"inc-{now_ms()}-{uuid.uuid4().hex[:6]}"
        notes: dict[str, Any] = {"sensor_name": sensor.get("name"), "camera_role": role,
                                 "controlled_test": bool((ev.raw.get("meta") or {}).get("controlled_test"))}
        self.db.insert_incident({
            "id": incident_id, "account_id": account_id, "sensor_device_id": ev.device_id, "room": room,
            "kind": kind, "status": "open", "opened_at_ms": ev.timestamp_ms or now_ms(), "opened_source": source,
            "camera_device_id": camera_id, "camera_role": role, "notes": notes,
        })
        log.info("incident %s opened (%s in %s, camera=%s/%s)", incident_id, kind, room, camera_id, role)

        # Chime first: it is the fastest thing a person can notice.
        try:
            client = self.ring.client_for(account_id)
            results = await asyncio.to_thread(chime_mod.announce, client, self.db, account_id, kind)
            self.db.update_incident(incident_id, chime_status=json.dumps(results))
        except Exception as e:  # noqa: BLE001
            self.db.update_incident(incident_id, chime_status=json.dumps([{"status": "error", "reason": str(e)[:200]}]))

        if role == "rover":
            self._rover_ready[incident_id] = asyncio.Event()
            cmd = Command(cmd="dispatch", incident_id=incident_id, route_id=sensor.get("route_id"),
                          sensor_device_id=ev.device_id, room=room)
            try:
                await self.dispatcher.send(cmd)
                self.db.update_incident(incident_id, rover_dispatched_at_ms=now_ms())
                self.db.insert_rover_log(incident_id, "dispatched", f"route {sensor.get('route_id')} to {room}",
                                         cmd.to_json())
            except Exception as e:  # noqa: BLE001
                self.db.insert_rover_log(incident_id, "error", f"dispatch failed: {e}")

        self._tasks[incident_id] = asyncio.create_task(self._capture_loop(incident_id), name=f"capture-{incident_id}")
        return self.db.get_incident(incident_id)

    def _pick_camera(self, sensor: dict[str, Any], account_id: str) -> tuple[str | None, str | None]:
        """A fixed camera that already sees the room wins; otherwise the rover's
        camera if the sensor has a route; otherwise no camera (the pack says so)."""
        if sensor.get("covered_by"):
            cam = self.db.get_device(sensor["covered_by"])
            if cam:
                return cam["device_id"], "fixed"
        if sensor.get("route_id"):
            for cam in self.db.list_devices(account_id=account_id, kind="camera"):
                if (cam.get("room") or "").lower() == "rover":
                    return cam["device_id"], "rover"
        # Fall back to any camera whose room matches the sensor's room.
        for cam in self.db.list_devices(account_id=account_id, kind="camera"):
            if cam.get("room") and sensor.get("room") and cam["room"].lower() == sensor["room"].lower():
                return cam["device_id"], "fixed"
        return None, None

    # --------------------------------------------------------------- capture

    async def _capture_loop(self, incident_id: str) -> None:
        inc = self.db.get_incident(incident_id)
        if not inc:
            return
        camera_id = inc.get("camera_device_id")
        if not camera_id:
            self.db.insert_capture_attempt(incident_id=incident_id, device_id=None, session_no=0,
                                           started_ms=now_ms(), ended_ms=now_ms(), frames=0, outcome="no_camera",
                                           detail="no camera covers this room and no rover route is configured")
            return
        if inc.get("camera_role") == "rover":
            ready = self._rover_ready.get(incident_id)
            try:
                if ready is not None:
                    await asyncio.wait_for(ready.wait(), timeout=self.settings.rover_wait_s)
            except asyncio.TimeoutError:
                self.db.insert_rover_log(incident_id, "error",
                                         f"rover did not report on_station within {self.settings.rover_wait_s} s; capturing anyway")
        if self.settings.first_capture_delay_s:
            await asyncio.sleep(self.settings.first_capture_delay_s)

        session_no = 0
        try:
            while True:
                inc = self.db.get_incident(incident_id)
                if not inc or inc["status"] != "open":
                    return
                session_no += 1
                await self._capture_once(inc, session_no)
                # Reconcile the sensor before sleeping: a missed flood_cleared must not keep us capturing.
                if await self._sensor_cleared(inc):
                    await self.close_incident(incident_id, now_ms(), "reconciled")
                    return
                await asyncio.sleep(self.settings.capture_interval_s)
        except asyncio.CancelledError:
            return

    async def _capture_once(self, inc: dict[str, Any], session_no: int) -> None:
        incident_id, camera_id = inc["id"], inc["camera_device_id"]
        client = self.ring.client_for(inc["account_id"])
        started = now_ms()
        try:
            st = await asyncio.to_thread(client.status, camera_id)
            self.db.insert_health(incident_id=incident_id, device_id=camera_id, ts_ms=now_ms(),
                                  online=int(st.online), source="status")
            if not st.online:
                self.db.insert_capture_attempt(incident_id=incident_id, device_id=camera_id, session_no=session_no,
                                               started_ms=started, ended_ms=now_ms(), frames=0,
                                               outcome="skipped_offline", detail="camera offline at session start")
                return
        except Exception as e:  # noqa: BLE001
            log.warning("status check failed: %s", e)

        result = await self.capture.capture(client, camera_id, self.settings.capture_session_s, self.settings.capture_fps)
        stored = 0
        for i, fr in enumerate(result.frames):
            key = f"incidents/{incident_id}/frames/{session_no:03d}-{i:03d}.jpg"
            self.blobs.put(key, fr.data, fr.content_type)
            # Caption the first, the last and every tenth frame; captioning every
            # frame at 1 fps would cost more than it tells.
            cap = await self._caption(fr, inc) if (i == 0 or i == len(result.frames) - 1 or i % 10 == 0) else None
            self.db.insert_frame(incident_id=incident_id, device_id=camera_id, session_no=session_no,
                                 requested_ms=fr.requested_ms, media_ms=fr.media_ms, origin=fr.origin,
                                 drift_ms=fr.drift_ms, path=key,
                                 caption=cap[0] if cap else None, caption_model=cap[1] if cap else None,
                                 water_visible=cap[2] if cap else None)
            stored += 1
        self.db.insert_capture_attempt(incident_id=incident_id, device_id=camera_id, session_no=session_no,
                                       started_ms=result.started_ms or started, ended_ms=result.ended_ms or now_ms(),
                                       frames=stored, outcome=result.outcome if stored or result.outcome != "ok" else "ok",
                                       detail=(result.detail + (f" session={result.session_id}" if result.session_id else "")).strip())

    async def _caption(self, fr: Frame, inc: dict[str, Any]) -> tuple[str, str, int]:
        try:
            ctx = f"{inc.get('kind')} sensor in {inc.get('room')}"
            cap = await asyncio.to_thread(self.captioner.caption, fr.data, ctx)
            return cap.description, cap.model, int(cap.water_visible)
        except Exception as e:  # noqa: BLE001
            return f"(caption failed: {str(e)[:120]})", "error", 0

    async def _sensor_cleared(self, inc: dict[str, Any]) -> bool:
        try:
            client = self.ring.client_for(inc["account_id"])
            st = await asyncio.to_thread(client.status, inc["sensor_device_id"])
        except Exception as e:  # noqa: BLE001
            log.warning("sensor status failed: %s", e)
            return False
        faulted = st.flood_faulted if inc["kind"] == "flood" else st.freeze_faulted
        if faulted is None:
            return False
        if not faulted:
            self.db.insert_event(f"reconciled-{inc['id']}-clear", event_id=None,
                                 type=f"{inc['kind']}_cleared", device_id=inc["sensor_device_id"],
                                 account_id=inc["account_id"], timestamp_ms=now_ms(), source="reconciled",
                                 raw=st.raw)
            return True
        return False

    # --------------------------------------------------------------- close

    async def close_incident(self, incident_id: str, closed_at_ms: int, source: str) -> None:
        if incident_id in self._closing:
            return
        self._closing.add(incident_id)
        try:
            inc = self.db.get_incident(incident_id)
            if not inc or inc["status"] != "open":
                return
            self.db.update_incident(incident_id, status="closed", closed_at_ms=closed_at_ms, closed_source=source)
            task = self._tasks.pop(incident_id, None)
            if task and task is not asyncio.current_task():
                task.cancel()
            self._rover_ready.pop(incident_id, None)
            if inc.get("camera_role") == "rover":
                try:
                    await self.dispatcher.send(Command(cmd="return_home", incident_id=incident_id, route_id=None,
                                                       sensor_device_id=inc["sensor_device_id"], room=inc["room"]))
                    self.db.insert_rover_log(incident_id, "returned", "return_home sent")
                except Exception as e:  # noqa: BLE001
                    self.db.insert_rover_log(incident_id, "error", f"return_home failed: {e}")
            try:
                await asyncio.to_thread(self.pack_builder.build, incident_id)
            except Exception as e:  # noqa: BLE001
                log.exception("pack build failed for %s: %s", incident_id, e)
            log.info("incident %s closed (%s)", incident_id, source)
        finally:
            self._closing.discard(incident_id)

    # --------------------------------------------------------------- rover

    async def rover_report(self, incident_id: str, kind: str, message: str = "", data: dict | None = None) -> None:
        data = data or {}
        self.db.insert_rover_log(incident_id, kind, message, data)
        if kind == "on_station":
            self.db.update_incident(incident_id, rover_on_station_at_ms=data.get("ts_ms") or now_ms(),
                                    rover_stop_reason=data.get("stop_reason") or "on_station")
            ev = self._rover_ready.get(incident_id)
            if ev:
                ev.set()
        elif kind in ("blocked", "wet"):
            self.db.update_incident(incident_id, rover_stop_reason=kind)
            if kind == "wet":
                # Reaching wet floor is reaching the water; that is on station.
                self.db.update_incident(incident_id, rover_on_station_at_ms=data.get("ts_ms") or now_ms())
                ev = self._rover_ready.get(incident_id)
                if ev:
                    ev.set()
            elif kind == "blocked":
                ev = self._rover_ready.get(incident_id)
                if ev:
                    ev.set()   # capture from wherever it stopped; the pack will say it was blocked
        elif kind == "telemetry":
            self.db.insert_reading(incident_id=incident_id, device_id=data.get("rover_id", "rover"), source="wand",
                                   ts_ms=data.get("ts_ms") or now_ms(), temperature=data.get("temperature"),
                                   humidity=data.get("humidity"), water_raw=data.get("water_raw"))

    # ---------------------------------------------------------- reconcile

    async def reconcile(self) -> dict[str, int]:
        """Compare every sensor's `/status` with what we believe. Opens or closes
        incidents we would otherwise have missed, marked `reconciled`."""
        opened = closed = polled = 0
        for dev in self.db.list_devices(kind="flood_freeze"):
            account_id = dev.get("account_id")
            if not account_id:
                continue
            try:
                client = self.ring.client_for(account_id)
                st = await asyncio.to_thread(client.status, dev["device_id"])
            except Exception as e:  # noqa: BLE001
                log.debug("reconcile status failed for %s: %s", dev["device_id"], e)
                continue
            polled += 1
            self.db.upsert_device(dev["device_id"], last_status=st.raw, online=int(st.online))
            open_inc = self.db.open_incident_for_sensor(dev["device_id"])
            for kind, faulted in (("flood", st.flood_faulted), ("freeze", st.freeze_faulted)):
                if faulted and not open_inc:
                    env = make_event(f"{kind}_detected", dev["device_id"], account_id=account_id,
                                     request_id=f"reconciled-{dev['device_id']}-{kind}-{now_ms()}")
                    from ringpartner import parse_event
                    await self.handle_event(parse_event(env), source="reconciled")
                    opened += 1
                    open_inc = self.db.open_incident_for_sensor(dev["device_id"])
                elif open_inc and open_inc["kind"] == kind and faulted is False:
                    await self.close_incident(open_inc["id"], now_ms(), "reconciled")
                    closed += 1
                    open_inc = None
        # Environmental readings from Ring temp/humidity sensors while incidents are open.
        open_incs = self.db.list_incidents(status="open")
        if open_incs:
            for dev in self.db.list_devices(kind="temperature_humidity"):
                try:
                    st = await asyncio.to_thread(self.ring.client_for(dev["account_id"]).status, dev["device_id"])
                except Exception:  # noqa: BLE001
                    continue
                for inc in open_incs:
                    if inc["account_id"] == dev["account_id"]:
                        self.db.insert_reading(incident_id=inc["id"], device_id=dev["device_id"], source="ring",
                                               ts_ms=now_ms(), temperature=st.temperature, humidity=st.humidity,
                                               water_raw=None)
        return {"polled": polled, "opened": opened, "closed": closed}

    async def shutdown(self) -> None:
        for t in list(self._tasks.values()):
            t.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
