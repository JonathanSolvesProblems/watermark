from watermark import claimmap, integrity
from watermark.captions import RekognitionCaptioner, _extract_json
from watermark.chime import _pick_slot
from watermark.ring import infer_kind
from ringpartner.types import ChimeSlot, DeviceCapabilities, DeviceStatus


def test_integrity_flags_drift_and_reconciled():
    inc = {"id": "i", "kind": "flood", "opened_at_ms": 1000, "closed_at_ms": 61000, "camera_device_id": "cam",
           "camera_role": "fixed", "opened_source": "received"}
    frames = [{"id": 1, "media_ms": 16000, "drift_ms": 15000, "caption_model": "amazon.nova-lite-v1:0"},
              {"id": 2, "media_ms": 20000, "drift_ms": 500}]
    health = [{"device_id": "cam", "ts_ms": 30000, "online": 0}, {"device_id": "cam", "ts_ms": 40000, "online": 1}]
    captures = [{"session_no": 1, "outcome": "ok", "frames": 2, "started_ms": 15000, "ended_ms": 20000},
                {"session_no": 2, "outcome": "media_not_found", "frames": 0, "started_ms": 45000, "ended_ms": 50000, "detail": "x"}]
    events = [{"type": "flood_cleared", "source": "reconciled", "timestamp_ms": 61000}]
    out = integrity.compute(inc, frames, health, captures, events, [])
    kinds = {g["kind"] for g in out["gaps"]}
    assert "camera_offline" in kinds and "capture_media_not_found" in kinds
    fl = {f["kind"] for f in out["flags"]}
    assert "frame_drift" in fl and "reconciled_event" in fl and "model_captions" in fl
    assert out["stats"]["sensor_to_first_frame_s"] == 15.0
    assert out["verdict"] == "partial"


def test_integrity_sensor_only_when_no_camera():
    inc = {"id": "i", "kind": "flood", "opened_at_ms": 1000, "camera_device_id": None}
    out = integrity.compute(inc, [], [], [{"session_no": 0, "outcome": "no_camera", "frames": 0}], [], [])
    assert out["verdict"] == "sensor-only" and out["gaps"][0]["kind"] == "no_camera"


def test_claimmap_counts():
    pack = {
        "incident": {"id": "i", "kind": "flood", "room": "Water heater closet", "opened_at_ms": 1000,
                     "closed_at_ms": 601000, "opened_source": "received", "chime_status": "[...]"},
        "sensor": {"name": "Water heater sensor"},
        "frames": [{"id": 1, "media_ms": 5000, "caption": "Water along the baseboard", "caption_model": "amazon.nova-lite-v1:0"}],
        "readings": [{"humidity": 40.0, "temperature": 20.0}, {"humidity": 70.0, "temperature": 21.0}],
        "health": [{"online": 1}], "captures": [{"outcome": "ok"}], "rover_log": [{"kind": "dispatched"}],
        "events": [], "prior_incident_count": 2,
    }
    # The real questions from my June 2026 claim.
    out = claimmap.evaluate(pack)
    assert out["total"] == 7
    by_id = {r["id"]: r["status"] for r in out["rows"]}
    assert by_id["q1"] == "answered" and by_id["q2"] == "answered"
    assert by_id["q3"] == "partial" and by_id["q4"] == "partial"
    assert by_id["q5"] == by_id["q6"] == by_id["q7"] == "homeowner"
    assert (out["answered"], out["partial"], out["homeowner"], out["unanswered"]) == (2, 2, 3, 0)

    # Cause is refused by design whatever question set is loaded.
    out = claimmap.evaluate(pack, {"source": "t", "questions": [
        {"id": "c", "question": "What caused the water?", "answered_by": ["cause"], "by_design_unanswered": True}]})
    assert out["rows"][0]["status"] == "unanswered" and "By design" in out["rows"][0]["evidence"]

    # With no frames, the camera-based questions fall back honestly.
    out = claimmap.evaluate({**pack, "frames": []})
    by_id = {r["id"]: r["status"] for r in out["rows"]}
    assert by_id["q2"] == "unanswered" and by_id["q3"] == "unanswered"


def test_infer_kind():
    flood = DeviceStatus.from_json({"data": {"attributes": {"online": True, "reported_at": "x", "flood_detection": {"faulted": False}}}})
    cam = DeviceStatus.from_json({"data": {"attributes": {"online": True, "reported_at": "x"}}})
    assert infer_kind(flood, None) == "flood_freeze"
    assert infer_kind(cam, DeviceCapabilities(["AVC"], False, None)) == "camera"
    assert infer_kind(cam, DeviceCapabilities(None, True, 2)) == "chime"
    temp = DeviceStatus.from_json({"data": {"attributes": {"online": True, "reported_at": "x", "temperature": 21.0, "humidity": 40.0}}})
    assert infer_kind(temp, None) == "temperature_humidity"


def test_pick_slot_prefers_kind():
    slots = [ChimeSlot("ring-appstore-event-2", "freeze", "Freeze", None, False),
             ChimeSlot("ring-appstore-event-1", "water", "Water", None, False)]
    assert _pick_slot(slots, "flood").audio_ref == "water"
    assert _pick_slot(slots, "freeze").audio_ref == "freeze"
    assert _pick_slot([ChimeSlot("ring-appstore-event-1", "w", None, None, True)], "flood") is None


def test_extract_json_tolerates_fences():
    assert _extract_json('```json\n{"a": 1}\n```')["a"] == 1
    assert _extract_json('text before {"water_visible": true} after')["water_visible"] is True
    assert "description" in _extract_json("no json here")


class _FakeRekognition:
    def __init__(self, labels):
        self.labels = labels

    def detect_labels(self, **_):
        return {"Labels": [{"Name": n, "Confidence": c} for n, c in self.labels]}


def test_rekognition_never_says_dry():
    """It can say yes to water, never no: on a real flood it saw only 'Hardwood'."""
    wet = RekognitionCaptioner("us-east-1", client=_FakeRekognition([("Floor", 95.0), ("Water", 91.2)])).caption(b"x")
    assert wet.water_visible is True and wet.confidence == "high" and "Water 91%" in wet.description
    assert "not measured" in wet.extent and wet.model == "rekognition:DetectLabels"
    weak = RekognitionCaptioner("us-east-1", client=_FakeRekognition([("Floor", 95.0), ("Water", 60.0)])).caption(b"x")
    assert weak.water_visible is None
    dry = RekognitionCaptioner("us-east-1", client=_FakeRekognition([("Bird Feeder", 92.0)])).caption(b"x")
    assert dry.water_visible is None and dry.description == "Labels seen: Bird Feeder 92%."


def test_flooring_question_cites_rekognition_floor_labels():
    frames = [{"caption_model": "rekognition:DetectLabels", "caption": "Labels seen: Floor 100%, Hardwood 99%, Wood 98%."},
              {"caption_model": "rekognition:DetectLabels", "caption": "Labels seen: Hardwood 100%, Tile 61%."},
              {"caption_model": "amazon.nova-lite-v1:0", "caption": "Laminate 100% along the wall"}]
    assert claimmap._floor_labels(frames) == "Hardwood (100%), Tile (61%)"
    assert claimmap._floor_labels([{"caption_model": "rekognition:DetectLabels",
                                    "caption": "Labels seen: Bird Feeder 92%."}]) == ""
