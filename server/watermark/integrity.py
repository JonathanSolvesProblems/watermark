"""The evidence integrity section: everything the pack could not verify, said
out loud. This is a feature of the product, not a footnote. A judge, an adjuster
or the homeowner should be able to read it and know exactly how much to trust
each part of the timeline.

Ring's own tolerances drive the thresholds: image download returns the closest
decodable frame within ±10 s of the requested time, so any frame further than
that is flagged; `device_offline` lags the real loss of connectivity, so offline
windows are reported as "at least".
"""
from __future__ import annotations

from typing import Any

RING_IMAGE_TOLERANCE_MS = 10_000


def compute(incident: dict[str, Any], frames: list[dict[str, Any]], health: list[dict[str, Any]],
            captures: list[dict[str, Any]], events: list[dict[str, Any]], rover_log: list[dict[str, Any]],
            settings=None) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    opened = incident.get("opened_at_ms")
    closed = incident.get("closed_at_ms")

    # 1. Camera offline windows inside the incident.
    cam = incident.get("camera_device_id")
    if cam:
        offline_since: int | None = None
        for h in sorted((x for x in health if x.get("device_id") == cam), key=lambda x: x["ts_ms"]):
            if not h["online"] and offline_since is None:
                offline_since = h["ts_ms"]
            elif h["online"] and offline_since is not None:
                gaps.append({"kind": "camera_offline", "start_ms": offline_since, "end_ms": h["ts_ms"],
                             "text": "No visual evidence: camera offline (Ring reports offline after a heartbeat "
                                     "timeout, so the real gap may be longer)."})
                offline_since = None
        if offline_since is not None:
            gaps.append({"kind": "camera_offline", "start_ms": offline_since, "end_ms": closed,
                         "text": "No visual evidence: camera offline until the incident closed."})
    else:
        gaps.append({"kind": "no_camera", "start_ms": opened, "end_ms": closed,
                     "text": "No camera covered this room and no rover route was configured. Sensor log only."})

    # 2. Capture sessions that produced nothing.
    for c in captures:
        if c.get("outcome") not in ("ok",) and c.get("frames", 0) == 0:
            gaps.append({"kind": f"capture_{c.get('outcome')}", "start_ms": c.get("started_ms"),
                         "end_ms": c.get("ended_ms"),
                         "text": f"Capture session {c.get('session_no')} produced no frames ({c.get('outcome')}): "
                                 f"{c.get('detail') or ''}".strip()})

    # 3. Frames whose Ring timestamp is further than Ring's own tolerance from what was asked.
    for f in frames:
        d = f.get("drift_ms")
        if d is not None and abs(d) > RING_IMAGE_TOLERANCE_MS:
            flags.append({"kind": "frame_drift", "frame_id": f["id"], "media_ms": f["media_ms"],
                          "text": f"Frame {f['id']}: Ring returned a frame {abs(d) / 1000:.1f} s from the requested "
                                  f"time (documented tolerance is 10 s). Timestamp shown is Ring's, not the request."})

    # 4. Events we learned by polling rather than by webhook.
    for e in events:
        if e.get("source") == "reconciled":
            flags.append({"kind": "reconciled_event", "event": e.get("type"), "timestamp_ms": e.get("timestamp_ms"),
                          "text": f"{e.get('type')} was observed by polling the sensor's status, not received as a "
                                  f"webhook. The time is when Watermark noticed, not when it happened."})
    if incident.get("opened_source") == "reconciled":
        flags.append({"kind": "opened_by_reconcile", "timestamp_ms": opened,
                      "text": "This incident was opened by polling. Water may have been present for up to one "
                              "reconcile interval before the recorded start."})

    # 5. Rover outcomes that are not "arrived at the water".
    reason = incident.get("rover_stop_reason")
    if incident.get("camera_role") == "rover":
        if reason == "blocked":
            flags.append({"kind": "rover_blocked", "text": "The rover stopped short of the water because its path was "
                                                             "blocked. Frames were taken from where it stopped."})
        elif not incident.get("rover_on_station_at_ms"):
            flags.append({"kind": "rover_no_station", "text": "The rover never reported reaching the room. Frames, if any, "
                                                                "were captured from wherever the camera was."})
        for r in rover_log:
            if r.get("kind") == "error":
                flags.append({"kind": "rover_error", "timestamp_ms": r.get("ts_ms"), "text": r.get("message", "")})

    # 6. Captions are model output.
    models = sorted({f.get("caption_model") for f in frames if f.get("caption_model") and f.get("caption_model") not in ("error",)})
    if models:
        flags.append({"kind": "model_captions", "text": f"Frame captions were written by {', '.join(models)} and describe "
                                                          f"what is visible; they are not measurements and never state a cause."})
    if incident.get("notes"):
        try:
            import json
            notes = json.loads(incident["notes"]) if isinstance(incident["notes"], str) else incident["notes"]
            if notes.get("controlled_test"):
                flags.append({"kind": "controlled_test", "text": "Controlled test: the sensor was placed in water on "
                                                                   "purpose. Devices, timestamps and captures are real."})
        except Exception:  # noqa: BLE001
            pass

    stats = _stats(incident, frames, captures)
    return {"gaps": gaps, "flags": flags, "stats": stats,
            "verdict": _verdict(gaps, flags, stats)}


def _stats(incident: dict[str, Any], frames: list[dict[str, Any]], captures: list[dict[str, Any]]) -> dict[str, Any]:
    opened = incident.get("opened_at_ms")
    first_frame = min((f["media_ms"] for f in frames if f.get("media_ms")), default=None)
    on_station = incident.get("rover_on_station_at_ms")
    dispatched = incident.get("rover_dispatched_at_ms")
    ok = sum(1 for c in captures if c.get("outcome") == "ok")
    return {
        "frames": len(frames),
        "sessions_total": len(captures),
        "sessions_ok": ok,
        "sensor_to_first_frame_s": round((first_frame - opened) / 1000, 1) if opened and first_frame else None,
        "sensor_to_dispatch_s": round((dispatched - opened) / 1000, 1) if opened and dispatched else None,
        "sensor_to_on_station_s": round((on_station - opened) / 1000, 1) if opened and on_station else None,
        "duration_s": round((incident["closed_at_ms"] - opened) / 1000, 1) if opened and incident.get("closed_at_ms") else None,
    }


def _verdict(gaps, flags, stats) -> str:
    if stats.get("frames", 0) == 0:
        return "sensor-only"
    hard = [g for g in gaps if g["kind"] in ("camera_offline", "no_camera")] + \
           [f for f in flags if f["kind"] in ("rover_blocked", "rover_no_station", "opened_by_reconcile")]
    return "complete" if not hard else "partial"
