import json

import pytest

from ringwire import (SENSOR_EVENTS, NonceError, SignatureError, compute_nonce, is_fresh, make_event,
                         match_nonce, parse_event, sign, verify_and_parse, verify_signature)

KEY = "test-signing-key-0123456789"

# Shapes copied from Ring's docs: sensors/overview.md and notifications/motion_detection.md
FLOOD = {
    "meta": {"version": "1.1", "time": "2026-01-15T21:57:54.279Z", "request_id": "req-1", "account_id": "acct-9"},
    "data": {
        "id": "dev-flood_flood_detected_1789000000000",
        "type": "flood_detected",
        "attributes": {"source": "dev-flood", "source_type": "devices", "timestamp": 1789000000000},
        "relationships": {"devices": {"links": {"self": "/v1/devices/dev-flood"}}},
    },
}

TEMP = {
    "meta": {"version": "1.1", "time": "2026-01-15T21:57:54.279Z", "request_id": "req-2", "account_id": "acct-9"},
    "data": {
        "id": "x", "type": "temperature_exceeded",
        "attributes": {"source": "dev-temp", "source_type": "devices", "timestamp": 1789000000000,
                       "temperature": 26.8, "threshold_type": "max"},
    },
}

MOTION = {
    "meta": {"version": "1.1", "time": "2025-07-06T11:11:00Z", "request_id": "req-3", "account_id": "acct-9"},
    "data": {
        "id": "ev", "type": "motion_detected", "subType": "human",
        "attributes": {"source": "dev-cam", "source_type": "devices", "timestamp": 1699457230000},
        "relationships": {"devices": {"links": {"self": "/v1/devices/dev-cam"}}},
    },
}


def test_signature_is_hex_over_raw_bytes():
    raw = json.dumps(FLOOD).encode()
    sig = sign(raw, KEY)
    assert sig.startswith("sha256=") and len(sig) == 7 + 64
    assert verify_signature(raw, sig, KEY)
    # Re-serialised JSON with different whitespace must fail: Ring signs the wire bytes.
    assert not verify_signature(json.dumps(FLOOD, indent=2).encode(), sig, KEY)
    assert not verify_signature(raw, None, KEY)
    assert not verify_signature(raw, "sha256=" + "0" * 64, KEY)


def test_verify_and_parse_rejects_bad_signature():
    raw = json.dumps(FLOOD).encode()
    with pytest.raises(SignatureError):
        verify_and_parse(raw, "sha256=deadbeef", KEY)
    ev = verify_and_parse(raw, sign(raw, KEY), KEY)
    assert ev.type == "flood_detected"


def test_parse_flood_event_reads_source_not_id():
    ev = parse_event(FLOOD)
    assert ev.device_id == "dev-flood"
    assert ev.timestamp_ms == 1789000000000
    assert ev.request_id == "req-1"
    assert ev.account_id == "acct-9"
    assert ev.is_sensor and ev.is_known
    assert ev.device_path == "/v1/devices/dev-flood"
    assert ev.reading is None


def test_parse_threshold_event_carries_reading():
    ev = parse_event(json.dumps(TEMP))
    assert ev.reading == 26.8
    assert ev.threshold_type == "max"
    assert ev.is_sensor


def test_parse_motion_subtype():
    ev = parse_event(MOTION)
    assert ev.sub_type == "human"
    assert not ev.is_sensor


def test_make_event_round_trips():
    env = make_event("flood_cleared", "dev-flood", timestamp_ms=123, request_id="r")
    ev = parse_event(env)
    assert ev.type == "flood_cleared" and ev.device_id == "dev-flood" and ev.timestamp_ms == 123
    assert ev.request_id == "r"
    assert "flood_cleared" in SENSOR_EVENTS


def test_nonce_matches_doc_algorithm():
    # URL-safe base64, no padding, over "<time_ms>:<account_id>"
    n = compute_nonce(KEY, 1771130906289, "acct-9")
    assert "=" not in n and "+" not in n and "/" not in n
    assert match_nonce(KEY, n, 1771130906289, ["acct-1", "acct-9"], now_ms=1771130906289 + 1000) == "acct-9"
    with pytest.raises(NonceError):
        match_nonce(KEY, n, 1771130906289, ["acct-1"], now_ms=1771130906289 + 1000)
    with pytest.raises(NonceError):
        match_nonce(KEY, n, 1771130906289, ["acct-9"], now_ms=1771130906289 + 601_000)


def test_is_fresh_window():
    assert is_fresh(1000, now_ms=1000 + 599_000)
    assert not is_fresh(1000, now_ms=1000 + 601_000)
