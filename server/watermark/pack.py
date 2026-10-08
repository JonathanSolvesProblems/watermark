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
        return tpl.render(pack=pack, thumbs=thumbs, chart=readings_svg(pack["readings"]), staff=staff_svg(pack))

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
        # A recording download carries Ring's X-Media-Timestamp; a live-session frame is
        # stamped on receipt, with Ring's own time burned into the image.
        stamp = ("received from the live session; Ring's time is in the image" if first.get("origin") == "live"
                 else "Ring media timestamp")
        items.append({"ts_ms": first["media_ms"], "kind": "first_frame", "source": "ring",
                      "text": f"First frame ({stamp})"})
    items.sort(key=lambda x: (x.get("ts_ms") or 0))
    return items


def staff_svg(pack: dict[str, Any], width: int = 860) -> str:
    """The flood staff gauge, same as the app's: an enamel staff with E-ticks, the time
    water stood as the one pink fill, frames as notches (pink where a caption saw water),
    unverified spans hatched. Drawn as SVG so it survives printing and PDF export."""
    inc = pack["incident"]
    start = inc.get("opened_at_ms")
    if not start:
        return ""
    end = inc.get("closed_at_ms") or int(time.time() * 1000)
    span = max(end - start, 1000)
    axis = span * (1.04 if inc.get("closed_at_ms") else 1.12)
    left, right, top, h = 2, width - 2, 22, 54
    w = right - left

    def x(ms: float) -> float:
        return left + max(0.0, min(1.0, (ms - start) / axis)) * w

    step = next((s * 1000 for s in (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 21600)
                 if axis / (s * 1000) <= 8), 43_200_000)
    parts = [f'<svg viewBox="0 0 {width} {top + h + 26}" width="100%" role="img" '
             f'aria-label="Water stood {_elapsed(span)}">',
             '<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" '
             'patternTransform="rotate(45)"><rect width="2" height="7" fill="#141816" fill-opacity=".55"/></pattern></defs>']
    for f in pack.get("frames", []):
        if f.get("media_ms"):
            colour = "var(--wet)" if f.get("water_visible") == 1 else "var(--ink)"
            parts.append(f'<rect x="{x(f["media_ms"]) - 1:.1f}" y="4" width="2.5" height="14" style="fill:{colour}"/>')
    parts.append(f'<rect x="{left}" y="{top}" width="{w}" height="{h}" fill="#f7f7f2" stroke="#141816"/>')
    parts.append(f'<rect x="{left}" y="{top}" width="{x(end) - left:.1f}" height="{h}" style="fill:var(--wet)"/>')
    for g in pack.get("integrity", {}).get("gaps", []):
        gx = x(g["start_ms"])
        parts.append(f'<rect x="{gx:.1f}" y="{top}" width="{max(2.0, x(g.get("end_ms") or end) - gx):.1f}" '
                     f'height="{h}" fill="url(#hatch)" stroke="#141816"/>')
    minor = step / 5
    i = 1
    while i * minor < axis:
        tx = x(start + i * minor)
        major = i % 5 == 0
        parts.append(f'<rect x="{tx - (1.5 if major else 0.5):.1f}" y="{top}" width="{3 if major else 1}" '
                     f'height="{h if major else h * 0.42:.1f}" fill="#141816"/>')
        if major:
            parts.append(f'<text x="{tx:.1f}" y="{top + h + 18}" font-size="12" text-anchor="middle" '
                         f'class="tick">{_elapsed(i * minor)}</text>')
        i += 1
    parts.append(f'<text x="{left}" y="{top + h + 18}" font-size="12" class="tick">0s</text></svg>')
    return "".join(parts)


def _elapsed(ms: float) -> str:
    s = max(0, round(ms / 1000))
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}" if s else f"{m}m"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}" if m else f"{h}h"


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
        return (f'<polyline fill="none" style="stroke:{color}" stroke-width="2" points="{coords}"/>'
                f'<text x="{width - 18}" y="14" font-size="11" style="fill:{color}" text-anchor="end">{key} {lo:.0f} to {hi:.0f}</text>')

    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="readings">'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>'
            f'{line("humidity", "var(--ink)")}{line("temperature", "var(--stencil)")}</svg>')


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
