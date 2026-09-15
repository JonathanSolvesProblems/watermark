"""End to end in mock mode: flood → chime → rover dispatched → rover on station →
frames captured and captioned → flood cleared → pack built with integrity and
claim mapping. No Ring, no AWS, no hardware."""
import asyncio
import json

import pytest

from ringpartner import make_event, sign
from watermark.ring import MockRing

from .conftest import wait_for


async def _rover_take_dispatch(client, token="dev-rover-token"):
    r = await client.get("/rover/commands", params={"rover_id": "rover-1", "wait": 2}, headers={"X-Rover-Token": token})
    assert r.status_code == 200
    return r.json()["command"]


@pytest.mark.asyncio
async def test_flood_to_pack(client, app):
    s = app.state.wm
    # 1. water touches the sensor
    r = await client.post("/api/test/trigger", json={"kind": "flood", "action": "detected"})
    assert r.status_code == 200 and r.json()["status"] == "opened"
    incident_id = r.json()["incident_id"]
    inc = s.db.get_incident(incident_id)
    assert inc["status"] == "open" and inc["camera_role"] == "rover" and inc["room"] == "Water heater closet"

    # 2. chime played (the one write in the API)
    played = MockRing.instance(s.settings).played
    assert played and played[0][1] == "mock-audio-water"
    chime = json.loads(inc["chime_status"])
    assert chime[0]["status"] == "completed"

    # 3. rover receives the dispatch and reports on station with wand telemetry
    cmd = await _rover_take_dispatch(client)
    assert cmd["cmd"] == "dispatch" and cmd["route_id"] == "route-water-heater" and cmd["incident_id"] == incident_id
    await client.post("/rover/report", headers={"X-Rover-Token": "dev-rover-token"},
                      json={"incident_id": incident_id, "kind": "ack", "message": "route loaded"})
    await client.post("/rover/report", headers={"X-Rover-Token": "dev-rover-token"},
                      json={"incident_id": incident_id, "kind": "telemetry",
                            "data": {"humidity": 61.0, "temperature": 21.5, "water_raw": 12}})
    await client.post("/rover/report", headers={"X-Rover-Token": "dev-rover-token"},
                      json={"incident_id": incident_id, "kind": "wet", "message": "wand touched water at 3.1 m",
                            "data": {"stop_reason": "wet"}})

    # 4. frames arrive from the (mock) Ring camera and get captioned
    frames = await wait_for(lambda: s.db.frames_for_incident(incident_id), timeout=8)
    assert frames, "capture loop produced no frames"
    assert all(f["origin"] == "mock" for f in frames)
    assert any(f["caption"] for f in frames)
    inc = s.db.get_incident(incident_id)
    assert inc["rover_on_station_at_ms"] is not None and inc["rover_stop_reason"] == "wet"

    # 5. the water is gone
    r = await client.post("/api/test/trigger", json={"kind": "flood", "action": "cleared"})
    assert r.json()["status"] == "closed"
    pack_row = await wait_for(lambda: s.db.latest_pack(incident_id), timeout=8)
    assert pack_row and pack_row["questions_total"] == 12

    # 6. the pack says what it can and cannot prove
    r = await client.get(f"/api/incidents/{incident_id}")
    pack = r.json()
    assert pack["integrity"]["stats"]["frames"] >= 1
    assert pack["integrity"]["stats"]["sensor_to_first_frame_s"] is not None
    assert pack["claims"]["answered"] >= 6
    cause = [q for q in pack["claims"]["rows"] if q["id"] == "q12"][0]
    assert cause["status"] == "unanswered" and "By design" in cause["evidence"]
    kinds = {f["kind"] for f in pack["integrity"]["flags"]}
    assert "controlled_test" in kinds and "model_captions" in kinds
    assert pack["readings"] and pack["readings"][0]["source"] == "wand"
    assert pack["aftermath"]["available"] and pack["aftermath"]["frames_analyzed"] >= 1

    # 7. artefacts exist
    html = (await client.get(f"/api/incidents/{incident_id}/pack.html")).text
    assert "Controlled test. Real device." in html and "Evidence integrity" in html
    assert (await client.get(f"/api/incidents/{incident_id}/pack.json")).status_code == 200
    img = await client.get(f"/api/frames/{frames[0]['id']}.jpg")
    assert img.status_code == 200 and img.content[:2] == b"\xff\xd8"

    # 8. return_home was sent to the rover
    cmd = await _rover_take_dispatch(client)
    assert cmd and cmd["cmd"] == "return_home"


@pytest.mark.asyncio
async def test_fixed_camera_path_without_rover(client, app):
    s = app.state.wm
    # Point the sensor at the fixed basement cam instead of a rover route.
    r = await client.patch(f"/api/devices/{MockRing.SENSOR}", json={"covered_by": MockRing.FIXED_CAM, "route_id": ""})
    assert r.status_code == 200 and r.json()["covered_by"] == MockRing.FIXED_CAM and r.json()["route_id"] is None
    r = await client.post("/api/test/trigger", json={"kind": "flood", "action": "detected"})
    incident_id = r.json()["incident_id"]
    inc = s.db.get_incident(incident_id)
    assert inc["camera_role"] == "fixed" and inc["camera_device_id"] == MockRing.FIXED_CAM
    assert inc["rover_dispatched_at_ms"] is None
    frames = await wait_for(lambda: s.db.frames_for_incident(incident_id), timeout=8)
    assert frames
    await client.post("/api/test/trigger", json={"kind": "flood", "action": "cleared"})
    pack_row = await wait_for(lambda: s.db.latest_pack(incident_id), timeout=8)
    assert pack_row


@pytest.mark.asyncio
async def test_camera_offline_becomes_a_gap(client, app):
    s = app.state.wm
    await client.post("/api/devices/discover")
    r = await client.post("/api/test/trigger", json={"kind": "flood", "action": "detected"})
    incident_id = r.json()["incident_id"]
    await _rover_take_dispatch(client)
    await client.post("/rover/report", headers={"X-Rover-Token": "dev-rover-token"},
                      json={"incident_id": incident_id, "kind": "on_station"})
    await wait_for(lambda: s.db.frames_for_incident(incident_id), timeout=8)
    await client.post("/api/test/camera-online", params={"online": "false", "device_id": MockRing.CAM})
    await asyncio.sleep(1.5)   # a capture attempt must see the camera offline and skip
    await client.post("/api/test/camera-online", params={"online": "true", "device_id": MockRing.CAM})
    await asyncio.sleep(0.2)
    await client.post("/api/test/trigger", json={"kind": "flood", "action": "cleared"})
    await wait_for(lambda: s.db.latest_pack(incident_id), timeout=8)
    pack = (await client.get(f"/api/incidents/{incident_id}")).json()
    kinds = [g["kind"] for g in pack["integrity"]["gaps"]]
    assert "camera_offline" in kinds, kinds
    assert any(c["outcome"] == "skipped_offline" for c in pack["captures"])
    assert pack["integrity"]["verdict"] == "partial"


@pytest.mark.asyncio
async def test_webhook_signature_and_dedupe(client, app):
    s = app.state.wm
    env = make_event("flood_detected", MockRing.SENSOR, account_id=MockRing.ACCOUNT, request_id="req-A")
    raw = json.dumps(env).encode()
    bad = await client.post("/webhooks/ring", content=raw, headers={"Content-Type": "application/json",
                                                                    "X-Signature": "sha256=" + "0" * 64})
    assert bad.status_code == 401
    good = await client.post("/webhooks/ring", content=raw, headers={"Content-Type": "application/json",
                                                                     "X-Signature": sign(raw, s.settings.ring_hmac_key)})
    assert good.status_code == 200 and good.json()["status"] == "accepted"
    await wait_for(lambda: s.db.open_incident_for_sensor(MockRing.SENSOR), timeout=3)
    # Ring retries with the same request_id: must be a no-op.
    again = await client.post("/webhooks/ring", content=raw, headers={"Content-Type": "application/json",
                                                                      "X-Signature": sign(raw, s.settings.ring_hmac_key)})
    assert again.status_code == 200
    await asyncio.sleep(0.2)
    assert len(s.db.list_incidents(status="open")) == 1
    assert len(s.db.query("SELECT * FROM events WHERE request_id='req-A'")) == 1


@pytest.mark.asyncio
async def test_reconcile_opens_and_closes_missed_incidents(client, app):
    s = app.state.wm
    mock = MockRing.instance(s.settings)
    mock.set_faulted(MockRing.SENSOR, True)          # water, but the webhook never arrived
    r = await client.post("/api/test/reconcile")
    assert r.json()["opened"] == 1
    inc = s.db.open_incident_for_sensor(MockRing.SENSOR)
    assert inc and inc["opened_source"] == "reconciled"
    mock.set_faulted(MockRing.SENSOR, False)         # dried, and that webhook was missed too
    r = await client.post("/api/test/reconcile")
    assert r.json()["closed"] == 1
    inc = s.db.get_incident(inc["id"])
    assert inc["status"] == "closed" and inc["closed_source"] == "reconciled"
    pack = (await client.get(f"/api/incidents/{inc['id']}")).json()
    assert any(f["kind"] == "opened_by_reconcile" for f in pack["integrity"]["flags"])


@pytest.mark.asyncio
async def test_rover_token_required(client):
    r = await client.get("/rover/commands", params={"wait": 0.1})
    assert r.status_code == 401
    r = await client.post("/rover/report", json={"incident_id": "x", "kind": "ack"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_removes_everything(client, app):
    s = app.state.wm
    r = await client.post("/api/test/trigger", json={"kind": "flood", "action": "detected"})
    incident_id = r.json()["incident_id"]
    await _rover_take_dispatch(client)
    await client.post("/rover/report", headers={"X-Rover-Token": "dev-rover-token"},
                      json={"incident_id": incident_id, "kind": "on_station"})
    frames = await wait_for(lambda: s.db.frames_for_incident(incident_id), timeout=8)
    assert frames
    r = await client.delete("/api/account")
    assert r.status_code == 200 and r.json()["deleted"]
    counts = r.json()["counts"]
    assert counts["incidents"] == 1 and counts["frames"] >= 1 and counts["blobs"] >= 1
    assert s.db.get_incident(incident_id) is None
    assert (await client.get(f"/api/frames/{frames[0]['id']}.jpg")).status_code == 404


@pytest.mark.asyncio
async def test_health_and_devices(client):
    assert (await client.get("/health")).json()["ok"]
    devs = (await client.get("/api/devices")).json()
    kinds = {d["device_id"]: d["kind"] for d in devs}
    assert kinds[MockRing.SENSOR] == "flood_freeze" and kinds[MockRing.CHIME] == "chime" and kinds[MockRing.CAM] == "camera"
    acct = (await client.get("/api/account")).json()
    assert acct["linked"] and acct["mode"] == "mock"
