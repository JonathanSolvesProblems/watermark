"""Build the evidence pack for one incident: a JSON document, an HTML page that
prints cleanly, and a PDF when Chromium is available through Playwright.

The pack is the product. Everything else in the server exists to fill it.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import brain_bridge, claimmap, integrity
from .blobs import BlobStore
from .captions import narrative
from .config import Settings
from .db import Database

log = logging.getLogger("watermark.pack")
TEMPLATES = Path(__file__).with_name("templates")


class PackBuilder:
    def __init__(self, settings: Settings, db: Database, blobs: BlobStore, questions_path: Path | None = None):
        self.settings = settings
        self.db = db
        self.blobs = blobs
        self.questions_path = questions_path
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
        self.env.filters["ts"] = fmt_ts
        self.env.filters["hms"] = fmt_hms

    def collect(self, incident_id: str) -> dict[str, Any]:
        inc = self.db.get_incident(incident_id)
        if not inc:
            raise KeyError(incident_id)
        frames = self.db.frames_for_incident(incident_id)
        readings = self.db.readings_for_incident(incident_id)
        health = self.db.health_for_incident(incident_id)
        captures = self.db.captures_for_incident(incident_id)
        rover_log = self.db.rover_log_for_incident(incident_id)
        for r in rover_log:
            try:
                r["data"] = json.loads(r["data"]) if isinstance(r.get("data"), str) else r.get("data")
            except Exception:  # noqa: BLE001
                pass
        # One minute either side is enough to catch the opening and closing webhooks
        # and any camera health events; wider windows drag in earlier incidents.
        since = (inc.get("opened_at_ms") or 0) - 60_000
        until = (inc.get("closed_at_ms") or None)
        events = [e for e in self.db.events_between(since, (until + 60_000) if until else None)
                  if e.get("account_id") == inc.get("account_id") or e.get("device_id") in
                  (inc.get("sensor_device_id"), inc.get("camera_device_id"))]
        for e in events:
            e.pop("raw", None)
        sensor = self.db.get_device(inc["sensor_device_id"]) or {}
        camera = self.db.get_device(inc["camera_device_id"]) if inc.get("camera_device_id") else None
        prior = [i for i in self.db.list_incidents(account_id=inc["account_id"], status="closed")
                 if i["id"] != incident_id and (i.get("opened_at_ms") or 0) < (inc.get("opened_at_ms") or 0)]
        try:
            notes = json.loads(inc["notes"]) if isinstance(inc.get("notes"), str) else (inc.get("notes") or {})
        except Exception:  # noqa: BLE001
            notes = {}
        try:
            chime = json.loads(inc["chime_status"]) if isinstance(inc.get("chime_status"), str) else (inc.get("chime_status") or [])
        except Exception:  # noqa: BLE001
            chime = []
        integ = integrity.compute(inc, frames, health, captures, events, rover_log, self.settings)
        pack: dict[str, Any] = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "incident": inc, "notes": notes, "chime": chime, "sensor": sensor, "camera": camera,
            "frames": frames, "readings": readings, "health": health, "captures": captures,
            "rover_log": rover_log, "events": events, "prior_incident_count": len(prior),
            "integrity": integ, "timeline": build_timeline(inc, events, frames, captures, rover_log, health, chime),
        }
        pack["claims"] = claimmap.evaluate(pack, claimmap.load_questions(self.questions_path))
        pack["aftermath"] = brain_bridge.analyze_frames(self.settings, self.blobs, frames)
        pack["narrative"] = narrative(inc, frames, readings, integ, self.settings)
        return pack

    def render_html(self, pack: dict[str, Any], inline_images: bool = True) -> str:
        tpl = self.env.get_template("pack.html")
        thumbs: dict[int, str] = {}
        if inline_images:
            for f in pack["frames"][:60]:
                try:
                    data = self.blobs.get(f["path"])
                    thumbs[f["id"]] = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
                except Exception:  # noqa: BLE001
                    continue
        return tpl.render(pack=pack, thumbs=thumbs, chart=readings_svg(pack["readings"]))

    def build(self, incident_id: str) -> dict[str, Any]:
        pack = self.collect(incident_id)
        html = self.render_html(pack)
        base = f"incidents/{incident_id}/pack"
        self.blobs.put(base + ".html", html.encode("utf-8"), "text/html")
        self.blobs.put(base + ".json", json.dumps(pack, indent=2, default=str).encode("utf-8"), "application/json")
        pdf_key = None
        try:
            pdf = html_to_pdf(html)
            if pdf:
                self.blobs.put(base + ".pdf", pdf, "application/pdf")
                pdf_key = base + ".pdf"
        except Exception as e:  # noqa: BLE001
            log.info("PDF not produced (%s); HTML pack is the deliverable", e)
        self.db.insert_pack(incident_id=incident_id, html_path=base + ".html", json_path=base + ".json",
                            pdf_path=pdf_key, questions_answered=pack["claims"]["answered"],
                            questions_total=pack["claims"]["total"])
        return pack


def fmt_ts(ms: int | None) -> str:
    if not ms:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ms / 1000))


def fmt_hms(ms: int | None) -> str:
    if not ms:
        return ""
    return time.strftime("%H:%M:%S", time.localtime(ms / 1000))


def build_timeline(inc, events, frames, captures, rover_log, health, chime) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for e in events:
        items.append({"ts_ms": e.get("timestamp_ms"), "kind": "event", "source": e.get("source"),
                      "text": f"{e.get('type')} from {e.get('device_id')}"})
    if chime:
        played = [c for c in chime if c.get("status") == "completed"]
        items.append({"ts_ms": inc.get("opened_at_ms"), "kind": "chime", "source": "ring",
                      "text": f"Chime played on {len(played)} device(s)" if played else
                              f"Chime not played: {'; '.join(str(c.get('reason', c.get('status'))) for c in chime)}"})
    for r in rover_log:
        if r.get("kind") == "telemetry":
            continue   # readings are charted; a line per sample is noise
        items.append({"ts_ms": r.get("ts_ms"), "kind": f"rover_{r.get('kind')}", "source": "rover",
                      "text": f"Rover {r.get('kind')}: {r.get('message')}"})
    for c in captures:
        items.append({"ts_ms": c.get("started_ms"), "kind": "capture", "source": "ring",
                      "text": f"Capture session {c.get('session_no')}: {c.get('frames')} frame(s), {c.get('outcome')}"})
    for h in health:
        items.append({"ts_ms": h.get("ts_ms"), "kind": "health", "source": h.get("source"),
                      "text": f"Camera {'online' if h.get('online') else 'OFFLINE'} ({h.get('source')})"})
    first = min((f for f in frames if f.get("media_ms")), key=lambda f: f["media_ms"], default=None)
    if first:
        items.append({"ts_ms": first["media_ms"], "kind": "first_frame", "source": "ring",
                      "text": "First frame (Ring media timestamp)"})
    items.sort(key=lambda x: (x.get("ts_ms") or 0))
    return items


def readings_svg(readings: list[dict[str, Any]], width: int = 720, height: int = 160) -> str:
    """Inline SVG of humidity (and temperature if present) over time. No library."""
    pts = [r for r in readings if r.get("ts_ms")]
    if len(pts) < 2:
        return ""
    t0, t1 = pts[0]["ts_ms"], pts[-1]["ts_ms"]
    span = max(1, t1 - t0)

    def line(key: str, color: str) -> str:
        vals = [(r["ts_ms"], r[key]) for r in pts if r.get(key) is not None]
        if len(vals) < 2:
            return ""
        lo = min(v for _, v in vals)
        hi = max(v for _, v in vals)
        rng = max(1e-6, hi - lo)
        coords = " ".join(f"{20 + (ts - t0) / span * (width - 40):.1f},{height - 20 - (v - lo) / rng * (height - 40):.1f}"
                          for ts, v in vals)
        return (f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{coords}"/>'
                f'<text x="{width - 18}" y="14" font-size="11" fill="{color}" text-anchor="end">{key} {lo:.0f} to {hi:.0f}</text>')

    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="readings">'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>'
            f'{line("humidity", "#2a6f9e")}{line("temperature", "#a0522d")}</svg>')


def html_to_pdf(html: str) -> bytes | None:
    """Playwright/Chromium when installed; otherwise None and the HTML stands."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        pdf = page.pdf(format="Letter", print_background=True, margin={"top": "14mm", "bottom": "14mm",
                                                                       "left": "12mm", "right": "12mm"})
        browser.close()
        return pdf
