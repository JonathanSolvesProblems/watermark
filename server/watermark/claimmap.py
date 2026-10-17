"""Map the pack's contents onto the insurer's claim questions.

Each question names the pack fields that satisfy it. A field is `answered` when
the pack holds concrete data for it, `partial` when it holds something related
but incomplete, and `unanswered` otherwise. Cause is unanswered by design: that
is the adjuster's determination, and a tool that guessed it would be worth less,
not more.

The headline number ("answers N of M questions on my claim file") comes out of
this module, graded by whatever questions are in `claim_questions.json`. Replace
the template questions with the real ones; the evaluation logic does not change.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_QUESTIONS = Path(__file__).with_name("claim_questions.json")


def load_questions(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_QUESTIONS
    return json.loads(p.read_text(encoding="utf-8"))


def evaluate(pack: dict[str, Any], questions: dict[str, Any] | None = None) -> dict[str, Any]:
    q = questions or load_questions()
    fields = _fields(pack)
    rows = []
    answered = partial = 0
    for item in q["questions"]:
        if item.get("by_design_unanswered"):
            rows.append({**item, "status": "unanswered", "evidence": "By design. Watermark records what happened; "
                                                                      "it does not determine cause."})
            continue
        if item.get("by_homeowner"):
            # About the house or the policy, not the incident: the homeowner answers these.
            rows.append({**item, "status": "homeowner", "evidence": "Yours to answer: this is about the house or the "
                                                                    "policy, not what the camera saw."})
            continue
        statuses = [fields.get(k, ("unanswered", "")) for k in item["answered_by"]]
        best = max(statuses, key=lambda s: {"answered": 2, "partial": 1, "unanswered": 0}[s[0]])
        if best[0] == "answered":
            answered += 1
        elif best[0] == "partial":
            partial += 1
        rows.append({**item, "status": best[0], "evidence": best[1]})
    homeowner = sum(1 for r in rows if r["status"] == "homeowner")
    return {"source": q.get("source"), "total": len(q["questions"]), "answered": answered, "partial": partial,
            "homeowner": homeowner, "unanswered": len(q["questions"]) - answered - partial - homeowner, "rows": rows}


def _fmt(ms: int | None) -> str:
    if not ms:
        return "n/a"
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ms / 1000))


FLOOR_MATERIALS = ("Hardwood", "Laminate", "Tile", "Carpet", "Vinyl", "Linoleum", "Concrete", "Marble")


def _floor_labels(frames: list[dict[str, Any]]) -> str:
    """The flooring material Rekognition named, with its best confidence, e.g. 'Hardwood (100%)'.
    Only what the labels say; it is the adjuster's question, so nothing is inferred."""
    best: dict[str, float] = {}
    for f in frames:
        if f.get("caption_model") != "rekognition:DetectLabels":
            continue
        for part in (f.get("caption") or "").removeprefix("Labels seen: ").rstrip(".").split(", "):
            name, _, pct = part.rpartition(" ")
            if name in FLOOR_MATERIALS and pct.endswith("%"):
                best[name] = max(best.get(name, 0.0), float(pct[:-1]))
    return ", ".join(f"{n} ({c:.0f}%)" for n, c in sorted(best.items(), key=lambda kv: -kv[1]))


def _fields(pack: dict[str, Any]) -> dict[str, tuple[str, str]]:
    inc = pack["incident"]
    frames = pack.get("frames", [])
    readings = pack.get("readings", [])
    health = pack.get("health", [])
    captures = pack.get("captures", [])
    rover = pack.get("rover_log", [])
    events = pack.get("events", [])
    out: dict[str, tuple[str, str]] = {}

    if inc.get("opened_at_ms"):
        src = "sensor webhook" if inc.get("opened_source") == "received" else inc.get("opened_source")
        out["first_detection_time"] = ("answered", f"{_fmt(inc['opened_at_ms'])} ({src})")
    out["location_in_home"] = ("answered", inc.get("room") or "") if inc.get("room") else ("unanswered", "")
    out["detection_source"] = ("answered", f"Ring {inc.get('kind')} sensor '{(pack.get('sensor') or {}).get('name', '')}'")
    if inc.get("closed_at_ms") and inc.get("opened_at_ms"):
        secs = (inc["closed_at_ms"] - inc["opened_at_ms"]) / 1000
        dur = f"{secs:.0f} seconds" if secs < 120 else f"{secs / 60:.0f} minutes"
        out["duration"] = ("answered", f"{dur}, from {_fmt(inc['opened_at_ms'])} to {_fmt(inc['closed_at_ms'])}")
    elif inc.get("opened_at_ms"):
        out["duration"] = ("partial", "incident still open; start time known")
    if frames:
        live = sum(1 for f in frames if f.get("origin") == "live")
        where = ("with Ring's time burned into each image" if live == len(frames)
                 else "with Ring media timestamps" if live == 0 else "with Ring timestamps (header or burned in)")
        out["photos_with_times"] = ("answered", f"{len(frames)} frames from the Ring camera {where}, first at "
                                                f"{_fmt(frames[0].get('media_ms'))}")
        # What the camera saw, not a judgement: the frames let the adjuster see where the
        # water was and whether it came from above ground. Watermark never names a source.
        out["water_entry_visible"] = ("answered", f"{len(frames)} timed frames of where the water was in "
                                                  f"{inc.get('room') or 'the room'}, for the adjuster to judge where it came in")
        floor = _floor_labels(frames)
        out["flooring_visible"] = ("partial", (f"Rekognition labels the floor in view as {floor}; damage and when it "
                                               f"was laid are the homeowner's to add") if floor else
                                              "the floor is in frame with Ring's time; what it is and when it was "
                                              "laid are the homeowner's to add")
        out["contents_visible"] = ("partial", "what was in the camera's view is on record with times; the itemized "
                                              "list and costs are the homeowner's")
    captions = [f for f in frames if f.get("caption") and f.get("caption_model") not in ("error", None)]
    if captions:
        real = [c for c in captions if c.get("caption_model") != "mock"]
        status = "answered" if real else "partial"
        out["extent_description"] = (status, captions[0]["caption"][:160] + (" (mock caption)" if not real else ""))
    if readings:
        hs = [r["humidity"] for r in readings if r.get("humidity") is not None]
        ts = [r["temperature"] for r in readings if r.get("temperature") is not None]
        parts = []
        if hs:
            parts.append(f"humidity {min(hs):.0f} to {max(hs):.0f}%")
        if ts:
            parts.append(f"temperature {min(ts):.1f} to {max(ts):.1f} C")
        out["environmental_readings"] = ("answered" if parts else "partial", f"{len(readings)} readings: " + ", ".join(parts))
    if health or captures:
        online = sum(1 for h in health if h.get("online"))
        out["device_health_log"] = ("answered", f"{len(health)} camera health checks ({online} online), "
                                                f"{len(captures)} capture sessions logged, sensor battery/signal in status log")
    prior = pack.get("prior_incident_count")
    if prior is not None:
        out["prior_incidents"] = ("answered", f"{prior} earlier incident(s) recorded by Watermark at this account")
    contacts = [e for e in events if e.get("type", "").startswith("contact_sensor")]
    if contacts:
        out["people_present"] = ("partial", f"{len(contacts)} door contact event(s) during the incident; identities unknown")
    else:
        out["people_present"] = ("unanswered", "no contact sensor events; Watermark does not identify people")
    actions = []
    if inc.get("chime_status"):
        actions.append("chime announced")
    if any(r.get("kind") == "dispatched" for r in rover):
        actions.append("camera dispatched to the room")
    if actions:
        out["actions_taken"] = ("partial", ", ".join(actions) + "; mitigation by people is not recorded")
    return out
