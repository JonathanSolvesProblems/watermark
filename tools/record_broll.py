#!/usr/bin/env python3
"""Record the demo's screen b-roll from a running Watermark (web + server) with Playwright.

Each shot is its own 1920x1080 clip in the design's home theme (dark), with slow,
scripted scrolling so it cuts cleanly. Point it at a server holding real Playground
incidents; it never seeds anything.

    py tools/record_broll.py --web http://localhost:3001 --api http://127.0.0.1:8766 --incident <id>
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

OUT = Path(__file__).resolve().parents[1] / "demo" / "broll"


def settle(page: Page, seconds: float) -> None:
    page.evaluate("document.fonts.ready")
    time.sleep(seconds)


def glide(page: Page, to_selector: str | None = None, to_y: int | None = None, seconds: float = 3.0) -> None:
    """Scroll smoothly to an element or a y position over `seconds`, in small steps."""
    target = to_y
    if to_selector:
        target = page.evaluate(f"document.querySelector({to_selector!r}).getBoundingClientRect().top + scrollY - 90")
    start = page.evaluate("scrollY")
    steps = int(seconds * 30)
    for i in range(1, steps + 1):
        t = i / steps
        ease = t * t * (3 - 2 * t)
        page.evaluate(f"scrollTo(0, {start + (target - start) * ease})")
        time.sleep(seconds / steps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3001")
    ap.add_argument("--api", default="http://127.0.0.1:8766")
    ap.add_argument("--incident", required=True)
    ap.add_argument("--theme", default="dark")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    shots = {
        "01-dashboard": lambda p: (p.goto(a.web + "/dashboard"), settle(p, 3), glide(p, "#incidents-h", seconds=3), settle(p, 3)),
        "02-incident-gauge": lambda p: (p.goto(f"{a.web}/incident?id={a.incident}"), settle(p, 6)),
        "03-incident-frames": lambda p: (p.goto(f"{a.web}/incident?id={a.incident}"), settle(p, 2),
                                         glide(p, "#frames-h", seconds=3), settle(p, 4)),
        "04-incident-integrity": lambda p: (p.goto(f"{a.web}/incident?id={a.incident}"), settle(p, 1),
                                            glide(p, "#timeline-h", seconds=0.1), settle(p, 1),
                                            glide(p, "#claims-h", seconds=4), settle(p, 4)),
        "05-pack": lambda p: (p.goto(f"{a.api}/api/incidents/{a.incident}/pack.html"), settle(p, 4),
                              glide(p, to_y=1400, seconds=6), settle(p, 2),
                              glide(p, to_y=3200, seconds=6), settle(p, 3)),
        "06-link": lambda p: (p.goto(a.web + "/link"), settle(p, 4)),
        "07-setup": lambda p: (p.goto(a.web + "/setup"), settle(p, 4)),
        "08-home": lambda p: (p.goto(a.web + "/"), settle(p, 4), glide(p, to_y=700, seconds=3), settle(p, 2)),
    }
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name, run in shots.items():
            tmp = OUT / f".rec-{name}"
            ctx = b.new_context(viewport={"width": 1920, "height": 1080}, color_scheme=a.theme,
                                record_video_dir=str(tmp), record_video_size={"width": 1920, "height": 1080})
            ctx.add_init_script(f"localStorage.setItem('wm-theme','{a.theme}');localStorage.setItem('wm-tour-done','1')")
            page = ctx.new_page()
            run(page)
            video = page.video
            ctx.close()
            src = Path(video.path())
            dest = OUT / f"{name}.webm"
            dest.unlink(missing_ok=True)   # re-recording replaces the old take
            shutil.move(str(src), dest)
            shutil.rmtree(tmp, ignore_errors=True)
            print("recorded", name)
        b.close()

    # The real Ring frames, full size, for stills.
    pack = httpx.get(f"{a.api}/api/incidents/{a.incident}/pack.json", timeout=30).json()
    for f in pack["frames"][:3]:
        img = httpx.get(f"{a.web}/api/frames/{f['id']}.jpg", timeout=30)
        (OUT / f"ring-frame-{f['id']}.jpg").write_bytes(img.content)
    print("frames saved to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
