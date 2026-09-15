import httpx
import pytest

from ringpartner import MediaNotFound, RateLimited, RingClient, Unauthorized
from ringpartner.types import DeviceStatus

DEVICES = {
    "meta": {"time": "2026-01-01T00:00:00Z"},
    "data": [
        {"type": "devices", "id": "cam-1", "attributes": {"name": "Water heater cam"},
         "relationships": {"location": {"data": {"type": "locations", "id": "loc-1"}}}},
        {"type": "devices", "id": "flood-1", "attributes": {"name": "Water heater sensor"}},
        {"type": "devices", "id": "chime-1", "attributes": {"name": "Upstairs", "image_url": "https://x/y.png"}},
    ],
}

FLOOD_STATUS = {"data": {"type": "device-status", "id": "s", "attributes": {
    "flood_detection": {"faulted": True}, "freeze_detection": {"faulted": False},
    "tamper_detection": {"detected": False}, "sensor_reporting_state": {"value": "active"},
    "battery_status": {"percentage": 90}, "signal_strength": {"value": "good"},
    "online": True, "reported_at": "2026-01-15T21:58:08.213Z",
    "audio": {"snooze": {"active": None, "until": None}}, "state": None}}}

NEVER_REPORTED = {"data": {"attributes": {"online": False, "reported_at": "1970-01-01T00:00:00Z",
                                           "sensor_reporting_state": {"value": "active"}}}}

CHIME_CAPS = {"data": {"attributes": {"video": {"codecs": None}, "audio": {"customizable_slots": 2,
                                                                          "supported_actions": ["chime.play"]}}}}
CHIME_CONF = {"data": {"attributes": {"audio": {"customizable_slots": [
    {"event": "ring-appstore-event-2", "disabled": False, "audio_ref": "ref-2", "audio_name": "Ring Alert 3"},
    {"event": "ring-appstore-event-1", "disabled": False, "audio_ref": "ref-1", "audio_name": "Navi"},
], "volume": 4}}}}


def _make(handler):
    return RingClient("tok", transport=httpx.MockTransport(handler), max_retries=2)


def test_list_devices_and_status():
    def handler(req: httpx.Request):
        assert req.headers["Authorization"] == "Bearer tok"
        if req.url.path == "/v1/devices":
            return httpx.Response(200, json=DEVICES)
        if req.url.path == "/v1/devices/flood-1/status":
            return httpx.Response(200, json=FLOOD_STATUS)
        if req.url.path == "/v1/devices/never/status":
            return httpx.Response(200, json=NEVER_REPORTED)
        return httpx.Response(404, json={"errors": [{"code": "NOT_FOUND"}]})

    c = _make(handler)
    devs = c.list_devices()
    assert [d.id for d in devs] == ["cam-1", "flood-1", "chime-1"]
    assert devs[0].location_id == "loc-1"
    st = c.status("flood-1")
    assert st.flood_faulted is True and st.freeze_faulted is False and st.tamper_detected is False
    assert st.battery_percentage == 90 and st.online and st.has_reported
    never = c.status("never")
    assert never.reported_at is None and not never.has_reported


def test_status_absent_fields_are_none():
    st = DeviceStatus.from_json({"data": {"attributes": {"online": True, "reported_at": "2026-01-01T00:00:00Z"}}})
    assert st.flood_faulted is None and st.battery_percentage is None


def test_chime_detection_and_slots_sorted():
    def handler(req: httpx.Request):
        if req.url.path.endswith("/capabilities"):
            return httpx.Response(200, json=CHIME_CAPS)
        if req.url.path.endswith("/configurations"):
            return httpx.Response(200, json=CHIME_CONF)
        if req.url.path.endswith("/media/audio/playback"):
            body = req.read().decode()
            assert '"audio_ref": "ref-1"' in body or '"audio_ref":"ref-1"' in body
            return httpx.Response(200, json={"data": {"type": "audio", "id": "ref-1", "attributes": {"status": "completed"}}})
        return httpx.Response(404)

    c = _make(handler)
    caps = c.capabilities("chime-1")
    assert caps.chime_play and not caps.has_camera
    conf = c.configurations("chime-1")
    assert [s.event for s in conf.chime_slots] == ["ring-appstore-event-1", "ring-appstore-event-2"]
    assert c.play_chime("chime-1", conf.chime_slots[0].audio_ref) == "completed"


def test_image_download_two_step_and_headers():
    def handler(req: httpx.Request):
        if req.url.path.endswith("/media/image/download"):
            assert req.method == "POST"
            assert "Authorization" in req.headers
            return httpx.Response(303, headers={"Location": "https://download.example/x?sig=1"})
        if req.url.host == "download.example":
            assert "Authorization" not in req.headers  # presigned URL must not carry the Bearer
            return httpx.Response(200, content=b"\xff\xd8jpeg", headers={
                "Content-Type": "image/jpeg", "X-Media-Timestamp": "1699457235000", "X-Media-Origin": "recording"})
        return httpx.Response(404)

    c = _make(handler)
    img = c.download_image("cam-1", at_timestamp_ms=1699457230000)
    assert img.data.startswith(b"\xff\xd8")
    assert img.media_origin == "recording" and img.drift_ms == 5000


def test_image_download_416_maps_to_media_not_found():
    def handler(req: httpx.Request):
        if req.url.path.endswith("/media/image/download"):
            return httpx.Response(303, headers={"Location": "https://download.example/x"})
        return httpx.Response(416, json={"errors": [{"code": "MEDIA_NOT_FOUND", "detail": "no media"}]})

    with pytest.raises(MediaNotFound):
        _make(handler).download_image("cam-1", at_timestamp_ms=1)


def test_clip_download_partial():
    def handler(req: httpx.Request):
        if req.url.path.endswith("/media/video/download"):
            return httpx.Response(303, headers={"Location": "https://download.example/v"})
        return httpx.Response(206, content=b"mp4", headers={"X-Media-Timestamp": "5", "X-Media-Duration": "3000"})

    clip = _make(handler).download_clip("cam-1", timestamp_ms=0, duration_ms=5000)
    assert clip.partial and clip.media_duration_ms == 3000


def test_whep_session_create_and_close():
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path))
        if req.method == "POST":
            assert req.headers["Content-Type"] == "application/sdp"
            return httpx.Response(201, text="v=0 answer", headers={
                "Location": "https://api.amazonvision.com/v1/devices/cam-1/media/streaming/whep/sessions/zzz"})
        return httpx.Response(204)

    c = _make(handler)
    s = c.create_whep_session("cam-1", "v=0 offer")
    assert s.session_id == "zzz" and s.sdp_answer == "v=0 answer"
    c.close_whep_session(s)
    assert calls[-1] == ("DELETE", "/v1/devices/cam-1/media/streaming/whep/sessions/zzz")


def test_event_history_pagination_stops_on_empty_page():
    pages = {
        None: {"data": [{"type": "history-events", "id": "e1", "attributes": {"event_type": "on_demand", "start": 1, "end": 2},
                          "relationships": {"source": {"data": {"type": "devices", "id": "cam-1"}}}}],
               "links": {"next": "/v1/history/devices/cam-1/events?page[key]=k2"}},
        "k2": {"data": [], "links": {"next": "/v1/history/devices/cam-1/events?page[key]=k3"}},
    }

    def handler(req: httpx.Request):
        key = req.url.params.get("page[key]")
        assert req.url.params.get("event_types") == "on_demand,motion.human"
        return httpx.Response(200, json=pages[key])

    evs = list(_make(handler).iter_event_history("cam-1", ["on_demand", "motion.human"]))
    assert [e.id for e in evs] == ["e1"] and evs[0].device_id == "cam-1"


def test_retry_on_429_then_success(monkeypatch):
    monkeypatch.setattr("ringpartner.client.time.sleep", lambda s: None)
    n = {"i": 0}

    def handler(req: httpx.Request):
        n["i"] += 1
        if n["i"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"data": {"id": "acct-1", "attributes": {"email": "a@b.c"}}})

    me = _make(handler).me()
    assert me.account_id == "acct-1" and n["i"] == 2


def test_429_exhausts_retries(monkeypatch):
    monkeypatch.setattr("ringpartner.client.time.sleep", lambda s: None)
    c = _make(lambda req: httpx.Response(429, headers={"Retry-After": "2"}))
    with pytest.raises(RateLimited) as ei:
        c.me()
    assert ei.value.retry_after == 2.0


def test_401_is_unauthorized_without_retry():
    n = {"i": 0}

    def handler(req):
        n["i"] += 1
        return httpx.Response(401, json={"errors": [{"code": "UNAUTHORIZED"}]})

    with pytest.raises(Unauthorized):
        _make(handler).me()
    assert n["i"] == 1


def test_token_exchange_is_form_encoded():
    def handler(req: httpx.Request):
        assert req.headers["Content-Type"].startswith("application/x-www-form-urlencoded")
        body = req.read().decode()
        assert "grant_type=authorization_code" in body and "code_verifier=ver" in body
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r", "expires_in": 14400, "token_type": "Bearer"})

    t = RingClient.exchange_code("c", "id", "secret", "ver", transport=httpx.MockTransport(handler))
    assert t.access_token == "a" and t.expires_in == 14400


def test_integration_patch_requires_a_field():
    c = _make(lambda req: httpx.Response(200, json={"status": "completed"}))
    with pytest.raises(ValueError):
        c.update_integration()
    assert c.update_integration(status="completed")["status"] == "completed"


def test_rtsps_url():
    assert RingClient.rtsps_url("cam-1") == "rtsps://video.rtsp.amazonvision.com:322/v1/devices/cam-1/stream"
    assert RingClient.rtsps_url("cam-1", "T") == "rtsps://:T@video.rtsp.amazonvision.com:322/v1/devices/cam-1/stream"
