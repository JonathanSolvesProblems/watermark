"""Ring access for the server: a real `RingClient` per linked account with token
refresh, or a `MockRing` that behaves like a small Ring account (one flood
sensor, one indoor cam, one chime) so the whole pipeline runs with no
credentials.

Device kinds are inferred once at discovery time and stored, because Ring's
device resource carries no type field and capability keys are shared across
device families (the docs say not to infer type from capabilities alone; the
combination of status attributes and `chime.play` is the closest thing to a
type there is).
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any

from ringpartner import (Device, DeviceCapabilities, DeviceConfigurations, DeviceStatus, MediaImage, RingClient,
                         Unauthorized, WhepSession)
from ringpartner.types import ChimeSlot

from .config import Settings
from .db import Database, now_ms


def infer_kind(status: DeviceStatus, caps: DeviceCapabilities | None) -> str:
    if caps is not None and caps.chime_play and not caps.has_camera:
        return "chime"
    if status.flood_faulted is not None or status.freeze_faulted is not None:
        return "flood_freeze"
    if status.contact_faulted is not None:
        return "contact"
    if status.temperature is not None or status.humidity is not None:
        return "temperature_humidity"
    if caps is not None and caps.has_camera:
        return "camera"
    return "unknown"


class RingService:
    """Hands out a client per account and keeps tokens fresh."""

    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db

    def client_for(self, account_id: str) -> RingClient:
        if self.settings.is_mock:
            return MockRing.instance(self.settings)  # type: ignore[return-value]
        acct = self.db.get_account(account_id)
        if not acct or not acct.get("refresh_token"):
            raise Unauthorized(401, detail=f"no tokens stored for account {account_id}")

        def provider() -> str:
            row = self.db.get_account(account_id) or {}
            if row.get("access_token") and (row.get("expires_at") or 0) - 300 > time.time():
                return row["access_token"]
            toks = RingClient.refresh(row["refresh_token"], self.settings.ring_client_id or "",
                                      self.settings.ring_client_secret or "")
            self.db.upsert_account(account_id, access_token=toks.access_token, refresh_token=toks.refresh_token,
                                   expires_at=time.time() + toks.expires_in)
            return toks.access_token

        return RingClient(token_provider=provider, base_url=self.settings.ring_api_base)

    def store_tokens(self, account_id: str, access_token: str, refresh_token: str, expires_in: int,
                     link_status: str = "unclaimed", email: str | None = None) -> None:
        self.db.upsert_account(account_id, access_token=access_token, refresh_token=refresh_token,
                               expires_at=time.time() + expires_in, link_status=link_status, email=email)

    def refresh_all(self) -> int:
        """Ring rotates refresh tokens on every exchange and they die after ~30 days
        of not being used, so refresh proactively (the docs suggest daily)."""
        if self.settings.is_mock:
            return 0
        n = 0
        for acct in self.db.list_accounts():
            if not acct.get("refresh_token"):
                continue
            try:
                toks = RingClient.refresh(acct["refresh_token"], self.settings.ring_client_id or "",
                                          self.settings.ring_client_secret or "")
                self.db.upsert_account(acct["account_id"], access_token=toks.access_token,
                                       refresh_token=toks.refresh_token, expires_at=time.time() + toks.expires_in)
                n += 1
            except Exception as e:  # noqa: BLE001
                self.db.upsert_account(acct["account_id"], link_status=f"refresh_failed: {e}"[:120])
        return n

    def discover(self, account_id: str) -> list[dict[str, Any]]:
        """List devices, fetch status + capabilities for each, store the inferred kind."""
        client = self.client_for(account_id)
        out = []
        for d in client.list_devices():
            status = client.status(d.id)
            try:
                caps = client.capabilities(d.id)
            except Exception:  # noqa: BLE001
                caps = None
            kind = infer_kind(status, caps)
            existing = self.db.get_device(d.id) or {}
            chime_ref = None
            if kind == "chime":
                try:
                    conf = client.configurations(d.id)
                    if conf.chime_slots:
                        chime_ref = conf.chime_slots[0].audio_ref
                except Exception:  # noqa: BLE001
                    pass
            self.db.upsert_device(d.id, account_id=account_id, name=d.name, kind=kind,
                                  chime_audio_ref=chime_ref, last_status=status.raw, online=int(status.online),
                                  room=existing.get("room"), route_id=existing.get("route_id"),
                                  covered_by=existing.get("covered_by"))
            out.append(self.db.get_device(d.id))
        return out


# ------------------------------------------------------------------------------------
# Mock Ring: the smallest account that exercises every code path.
# ------------------------------------------------------------------------------------

@dataclass
class _MockDevice:
    id: str
    name: str
    kind: str
    faulted: bool = False
    online: bool = True


class MockRing:
    """Stands in for `RingClient`. Same method names, same return types.

    Frames are generated JPEGs stamped MOCK so nobody mistakes them for evidence.
    """

    _inst: "MockRing | None" = None
    SENSOR = "mock-flood-water-heater"
    CAM = "mock-cam-rover"
    FIXED_CAM = "mock-cam-fixed-basement"
    CHIME = "mock-chime-upstairs"
    ACCOUNT = "mock-account"

    @classmethod
    def instance(cls, settings: Settings) -> "MockRing":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self) -> None:
        self.devices = {
            self.SENSOR: _MockDevice(self.SENSOR, "Water heater sensor", "flood_freeze"),
            self.CAM: _MockDevice(self.CAM, "Rover cam", "camera"),
            self.FIXED_CAM: _MockDevice(self.FIXED_CAM, "Basement cam", "camera"),
            self.CHIME: _MockDevice(self.CHIME, "Upstairs chime", "chime"),
        }
        self.played: list[tuple[str, str]] = []
        self.sessions: list[WhepSession] = []
        self.flood_started_ms: int | None = None

    # -- test controls --
    def set_faulted(self, device_id: str, faulted: bool) -> None:
        self.devices[device_id].faulted = faulted
        self.flood_started_ms = now_ms() if faulted else None

    def set_online(self, device_id: str, online: bool) -> None:
        self.devices[device_id].online = online

    # -- RingClient surface --
    def me(self):
        from ringpartner import User
        return User(account_id=self.ACCOUNT, email="mock@example.com")

    def list_devices(self, include=None) -> list[Device]:
        return [Device(id=d.id, name=d.name) for d in self.devices.values()]

    def status(self, device_id: str, component_id=None) -> DeviceStatus:
        d = self.devices[device_id]
        attrs: dict[str, Any] = {"online": d.online, "reported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if d.kind == "flood_freeze":
            attrs.update({"flood_detection": {"faulted": d.faulted}, "freeze_detection": {"faulted": False},
                          "tamper_detection": {"detected": False}, "sensor_reporting_state": {"value": "active"},
                          "battery_status": {"percentage": 88}, "signal_strength": {"value": "good"}})
        if d.kind == "chime":
            attrs["audio"] = {"snooze": {"active": False, "until": None}}
        return DeviceStatus.from_json({"data": {"attributes": attrs}})

    def capabilities(self, device_id: str, component_id=None) -> DeviceCapabilities:
        d = self.devices[device_id]
        if d.kind == "camera":
            return DeviceCapabilities(video_codecs=["AVC"], chime_play=False, audio_slots=None)
        if d.kind == "chime":
            return DeviceCapabilities(video_codecs=None, chime_play=True, audio_slots=2)
        return DeviceCapabilities(video_codecs=None, chime_play=False, audio_slots=None)

    def configurations(self, device_id: str, component_id=None) -> DeviceConfigurations:
        d = self.devices[device_id]
        slots = []
        if d.kind == "chime":
            slots = [ChimeSlot("ring-appstore-event-1", "mock-audio-water", "Water detected", None, False),
                     ChimeSlot("ring-appstore-event-2", "mock-audio-freeze", "Freeze detected", None, False)]
        return DeviceConfigurations(motion_detection_enabled=None, chime_slots=slots, chime_volume=4,
                                    temperature_threshold=None, humidity_threshold=None)

    def play_chime(self, device_id: str, audio_ref: str) -> str:
        self.played.append((device_id, audio_ref))
        return "completed"

    def create_whep_session(self, device_id: str, sdp_offer: str, component_id=None) -> WhepSession:
        s = WhepSession(session_url=f"mock://sessions/{device_id}/{len(self.sessions) + 1}", sdp_answer="v=0",
                        device_id=device_id)
        self.sessions.append(s)
        return s

    def close_whep_session(self, session) -> None:
        return None

    def download_image(self, device_id: str, *, at_timestamp_ms=None, start_ms=None, end_ms=None, fmt="jpeg",
                       width=1280, height=720, component_id=None) -> MediaImage:
        ts = at_timestamp_ms if at_timestamp_ms is not None else now_ms()
        data = mock_frame(device_id, ts, self.flood_started_ms)
        return MediaImage(data=data, content_type="image/jpeg", media_timestamp_ms=ts + 1200,
                          media_origin="recording", requested_timestamp_ms=at_timestamp_ms)

    def event_history(self, *a, **k):
        from ringpartner import HistoryPage
        return HistoryPage(events=[], next_path=None)

    def iter_event_history(self, *a, **k):
        return iter(())

    def close(self) -> None:
        return None


def mock_frame(device_id: str, ts_ms: int, flood_started_ms: int | None, size=(960, 540)) -> bytes:
    """A synthetic frame that is unmistakably synthetic: grey room, a blue band that
    rises with time since the flood started, and a MOCK banner."""
    from PIL import Image, ImageDraw

    w, h = size
    img = Image.new("RGB", size, (58, 60, 66))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(h * 0.62), w, h], fill=(78, 74, 66))        # floor
    d.rectangle([int(w * 0.72), int(h * 0.18), int(w * 0.86), int(h * 0.64)], fill=(120, 122, 128))  # water heater
    elapsed_s = max(0, (ts_ms - flood_started_ms) / 1000.0) if flood_started_ms else 0
    depth_px = int(min(h * 0.16, 6 + elapsed_s * 0.05))
    d.rectangle([0, h - depth_px, w, h], fill=(38, 92, 150))          # water
    d.rectangle([0, 0, w, 44], fill=(180, 40, 40))
    d.text((14, 12), f"MOCK FRAME  {device_id}  {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts_ms / 1000))}Z",
           fill=(255, 255, 255))
    d.text((14, h - depth_px - 18), f"synthetic water band, {depth_px}px", fill=(230, 230, 230))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()
