"""Plain dataclasses for the parts of Ring's JSON:API responses an app actually reads.

The raw response is always kept on `.raw` so nothing is lost when Ring adds fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EPOCH_NEVER_REPORTED = "1970-01-01T00:00:00Z"

SensorKind = Literal["contact", "flood_freeze", "temperature_humidity", "air_quality"]


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str | None = None
    token_type: str = "Bearer"
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TokenSet":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=int(data.get("expires_in", 14400)),
            scope=data.get("scope"),
            token_type=data.get("token_type", "Bearer"),
            raw=data,
        )


@dataclass
class User:
    account_id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "User":
        d = data.get("data", data)
        attrs = d.get("attributes", {}) or {}
        return cls(
            account_id=str(d.get("id")),
            name=attrs.get("name") or attrs.get("first_name"),
            email=attrs.get("email"),
            phone=attrs.get("phone") or attrs.get("phone_number"),
            raw=data,
        )


@dataclass
class Device:
    id: str
    name: str
    image_url: str | None = None
    location_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Device":
        attrs = d.get("attributes", {}) or {}
        rel = d.get("relationships", {}) or {}
        loc = ((rel.get("location") or {}).get("data") or {}).get("id")
        return cls(id=str(d["id"]), name=attrs.get("name", ""), image_url=attrs.get("image_url"),
                   location_id=loc, raw=d)


@dataclass
class DeviceStatus:
    """Attributes of `GET /v1/devices/{id}/status`, flattened.

    Sensor detection attributes are booleans (`flood_faulted`, `freeze_faulted`,
    `contact_faulted`, `tamper_detected`) and are None when the device does not
    report them. `reported_at` is None when Ring returned the 1970 epoch, which
    means the device has never checked in; do not compare it as a real time.
    """

    online: bool
    reported_at: str | None
    battery_percentage: int | None = None
    signal_strength: str | None = None
    flood_faulted: bool | None = None
    freeze_faulted: bool | None = None
    contact_faulted: bool | None = None
    tamper_detected: bool | None = None
    temperature: float | None = None
    humidity: float | None = None
    snooze_active: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DeviceStatus":
        d = data.get("data", data)
        a = d.get("attributes", {}) or {}

        def faulted(key: str, sub: str = "faulted") -> bool | None:
            v = a.get(key)
            if not isinstance(v, dict) or sub not in v:
                return None
            return bool(v[sub])

        reported = a.get("reported_at")
        if reported == EPOCH_NEVER_REPORTED:
            reported = None
        batt = (a.get("battery_status") or {}).get("percentage") if isinstance(a.get("battery_status"), dict) else None
        sig = (a.get("signal_strength") or {}).get("value") if isinstance(a.get("signal_strength"), dict) else None
        snooze = ((a.get("audio") or {}).get("snooze") or {}).get("active") if isinstance(a.get("audio"), dict) else None
        return cls(
            online=bool(a.get("online", False)),
            reported_at=reported,
            battery_percentage=batt,
            signal_strength=sig,
            flood_faulted=faulted("flood_detection"),
            freeze_faulted=faulted("freeze_detection"),
            contact_faulted=faulted("contact_detection"),
            tamper_detected=faulted("tamper_detection", "detected"),
            temperature=a.get("temperature"),
            humidity=a.get("humidity"),
            snooze_active=snooze,
            raw=data,
        )

    @property
    def has_reported(self) -> bool:
        return self.reported_at is not None


@dataclass
class DeviceCapabilities:
    video_codecs: list[str] | None
    chime_play: bool
    audio_slots: int | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DeviceCapabilities":
        d = data.get("data", data)
        a = d.get("attributes", {}) or {}
        video = a.get("video") or {}
        audio = a.get("audio") or {}
        actions = audio.get("supported_actions") or []
        return cls(
            video_codecs=video.get("codecs"),
            chime_play="chime.play" in actions,
            audio_slots=audio.get("customizable_slots") if isinstance(audio.get("customizable_slots"), int) else None,
            raw=data,
        )

    @property
    def has_camera(self) -> bool:
        return bool(self.video_codecs)

    @property
    def hevc_only(self) -> bool:
        return self.video_codecs == ["HEVC"]


@dataclass
class ChimeSlot:
    event: str
    audio_ref: str
    audio_name: str | None
    audio_url: str | None
    disabled: bool


@dataclass
class DeviceConfigurations:
    motion_detection_enabled: bool | None
    chime_slots: list[ChimeSlot]
    chime_volume: int | None
    temperature_threshold: dict[str, float] | None
    humidity_threshold: dict[str, float] | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DeviceConfigurations":
        d = data.get("data", data)
        a = d.get("attributes", {}) or {}
        audio = a.get("audio") or {}
        slots_raw = audio.get("customizable_slots")
        slots: list[ChimeSlot] = []
        if isinstance(slots_raw, list):
            for s in slots_raw:
                slots.append(ChimeSlot(
                    event=s.get("event", ""), audio_ref=s.get("audio_ref", ""),
                    audio_name=s.get("audio_name"), audio_url=s.get("audio_url"),
                    disabled=bool(s.get("disabled", False)),
                ))
            # Ring does not return slots in event order.
            slots.sort(key=lambda s: s.event)
        md = a.get("motion_detection") or {}
        return cls(
            motion_detection_enabled=md.get("enabled") if isinstance(md, dict) else None,
            chime_slots=slots,
            chime_volume=audio.get("volume") if isinstance(audio, dict) else None,
            temperature_threshold=a.get("temperature_threshold"),
            humidity_threshold=a.get("humidity_threshold"),
            raw=data,
        )


@dataclass
class HistoryEvent:
    id: str
    event_type: str
    start_ms: int
    end_ms: int
    device_id: str | None
    third_party_reviewed: bool
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "HistoryEvent":
        a = d.get("attributes", {}) or {}
        src = (((d.get("relationships") or {}).get("source") or {}).get("data") or {}).get("id")
        return cls(id=str(d["id"]), event_type=a.get("event_type", ""), start_ms=int(a.get("start", 0)),
                   end_ms=int(a.get("end", 0)), device_id=src,
                   third_party_reviewed=bool(a.get("is_third_party_reviewed", False)), raw=d)


@dataclass
class HistoryPage:
    events: list[HistoryEvent]
    next_path: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaImage:
    data: bytes
    content_type: str
    media_timestamp_ms: int | None
    media_origin: str | None  # "recording" or "snapshot"
    requested_timestamp_ms: int | None = None

    @property
    def drift_ms(self) -> int | None:
        """How far the frame Ring returned is from the timestamp asked for."""
        if self.media_timestamp_ms is None or self.requested_timestamp_ms is None:
            return None
        return self.media_timestamp_ms - self.requested_timestamp_ms


@dataclass
class MediaClip:
    data: bytes
    media_timestamp_ms: int | None
    media_duration_ms: int | None
    partial: bool


@dataclass
class WhepSession:
    session_url: str
    sdp_answer: str
    device_id: str

    @property
    def session_id(self) -> str:
        return self.session_url.rstrip("/").rsplit("/", 1)[-1]
