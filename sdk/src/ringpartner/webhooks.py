"""Webhook verification and parsing.

Ring signs every webhook with HMAC-SHA256 over the raw body bytes using the
partner's HMAC signing key, hex encoded, sent as `X-Signature: sha256=<hex>`.
Verify against the raw bytes exactly as received; re-serialising the JSON
changes whitespace and breaks the signature.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

from .errors import SignatureError

SIGNATURE_HEADER = "X-Signature"

CAMERA_EVENTS = frozenset({"motion_detected", "button_press"})
DEVICE_EVENTS = frozenset({"device_added", "device_removed", "device_online", "device_offline"})
ACCOUNT_EVENTS = frozenset({
    "app_integration_added", "app_integration_removed",
    "subscription_activated", "subscription_deactivated",
})
SENSOR_STATE_EVENTS = frozenset({
    "contact_sensor_faulted", "contact_sensor_cleared",
    "tamper_detected", "tamper_cleared",
    "flood_detected", "flood_cleared",
    "freeze_detected", "freeze_cleared",
})
SENSOR_THRESHOLD_EVENTS = frozenset({
    "temperature_exceeded", "temperature_cleared",
    "humidity_exceeded", "humidity_cleared",
    "pm25_exceeded", "pm25_cleared",
    "co_exceeded", "co_cleared",
})
SENSOR_EVENTS = SENSOR_STATE_EVENTS | SENSOR_THRESHOLD_EVENTS
ALL_EVENTS = CAMERA_EVENTS | DEVICE_EVENTS | ACCOUNT_EVENTS | SENSOR_EVENTS


def sign(raw_body: bytes, signing_key: str) -> str:
    """Produce the `X-Signature` value Ring would send for this body. Used by tests
    and by anyone replaying captured webhooks into a local server."""
    digest = hmac.new(signing_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(raw_body: bytes, received: str | None, signing_key: str) -> bool:
    """Constant-time check of `X-Signature` against the raw body."""
    if not received:
        return False
    expected = sign(raw_body, signing_key)
    return hmac.compare_digest(expected, received.strip())


@dataclass
class WebhookEvent:
    """One webhook, flattened. `raw` keeps the full envelope."""

    type: str
    request_id: str
    account_id: str | None
    sent_at: str | None
    event_id: str | None
    device_id: str | None
    timestamp_ms: int | None
    sub_type: str | None = None
    reading: float | None = None          # temperature / humidity / pm25 / co on threshold events
    threshold_type: str | None = None     # "min" or "max" on *_exceeded events
    version: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_sensor(self) -> bool:
        return self.type in SENSOR_EVENTS

    @property
    def is_known(self) -> bool:
        return self.type in ALL_EVENTS

    @property
    def device_path(self) -> str | None:
        rel = ((self.raw.get("data") or {}).get("relationships") or {}).get("devices") or {}
        return (rel.get("links") or {}).get("self")


def parse_event(raw_body: bytes | str | dict[str, Any]) -> WebhookEvent:
    """Turn a v1.1 webhook envelope into a `WebhookEvent`.

    Reads the device from `data.attributes.source`, never by parsing `data.id`;
    Ring documents the id's structure as not a contract.
    """
    if isinstance(raw_body, (bytes, bytearray)):
        payload = json.loads(raw_body.decode("utf-8"))
    elif isinstance(raw_body, str):
        payload = json.loads(raw_body)
    else:
        payload = raw_body
    meta = payload.get("meta") or {}
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}
    reading = None
    for key in ("temperature", "humidity", "pm25", "co"):
        if key in attrs and isinstance(attrs[key], (int, float)):
            reading = float(attrs[key])
            break
    ts = attrs.get("timestamp")
    return WebhookEvent(
        type=str(data.get("type", "")),
        request_id=str(meta.get("request_id", "")),
        account_id=meta.get("account_id"),
        sent_at=meta.get("time"),
        event_id=data.get("id"),
        device_id=attrs.get("source"),
        timestamp_ms=int(ts) if isinstance(ts, (int, float)) else None,
        sub_type=data.get("subType") or attrs.get("sub_type"),
        reading=reading,
        threshold_type=attrs.get("threshold_type"),
        version=meta.get("version"),
        raw=payload,
    )


def verify_and_parse(raw_body: bytes, received_signature: str | None, signing_key: str) -> WebhookEvent:
    """The one call a webhook handler needs. Raises `SignatureError` on a bad signature."""
    if not verify_signature(raw_body, received_signature, signing_key):
        raise SignatureError("X-Signature did not match the raw body")
    return parse_event(raw_body)


def make_event(event_type: str, device_id: str, *, account_id: str = "acct_test",
               timestamp_ms: int | None = None, request_id: str | None = None,
               extra_attributes: dict[str, Any] | None = None,
               sub_type: str | None = None) -> dict[str, Any]:
    """Build a webhook envelope in Ring's v1.1 shape. For tests, the sandbox
    replay tool, and local development without a public webhook URL."""
    import time
    import uuid

    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    rid = request_id or uuid.uuid4().hex
    attrs: dict[str, Any] = {"source": device_id, "source_type": "devices", "timestamp": ts}
    if extra_attributes:
        attrs.update(extra_attributes)
    data: dict[str, Any] = {
        "id": f"{device_id}_{event_type}_{ts}",
        "type": event_type,
        "attributes": attrs,
        "relationships": {"devices": {"links": {"self": f"/v1/devices/{device_id}"}}},
    }
    if sub_type:
        data["subType"] = sub_type
    return {
        "meta": {
            "version": "1.1",
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts / 1000)),
            "request_id": rid,
            "account_id": account_id,
        },
        "data": data,
    }
