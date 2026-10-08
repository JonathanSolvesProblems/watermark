#!/usr/bin/env python3
"""Measure sensor-to-first-frame against the Ring Developer Playground, n times.

Needs a Watermark server in Playground mode (`.\\run-live.ps1 -Mode playground`, or
uvicorn with MODE=playground) and a fresh token in tmp/playground_token.txt. Each run
fires the simulated sensor, waits for frames from the real Ring live session, holds,
clears the sensor, waits for the pack, and saves the pack under docs/runs/playground/.
A summary with every value, the median and the range goes to
docs/runs/playground-series.json, which is what the docs may quote.

    py tools/playground_runs.py --runs 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "runs"


def wait(fn, timeout: float, step: float = 1.0):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return fn()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8765")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--hold", type=float, default=30, help="seconds to leave the sensor wet after the first frame")
    ap.add_argument("--gap", type=float, default=10, help="seconds between runs, so live sessions close")
    a = ap.parse_args()

    c = httpx.Client(base_url=a.server, timeout=60)
    acct = c.get("/api/account").json()
    if acct.get("mode") != "playground":
        print(f"server is in {acct.get('mode')!r} mode; start it with MODE=playground", file=sys.stderr)
        return 2
    # A leftover open incident would be reused by the first trigger and measure nothing new.
    for inc in c.get("/api/incidents").json():
        if inc["status"] == "open":
            c.post(f"/api/incidents/{inc['id']}/close")
            print(f"closed leftover incident {inc['id']}")
    # The Playground camera is online for roughly 16 minutes after a token is generated;
    # an offline camera accepts a live session and streams nothing.
    cams = [d for d in c.post("/api/devices/discover").json() if d.get("kind") == "camera"]
    if not cams or not all(d.get("online") for d in cams):
        print("Playground camera reports offline. Generate a fresh token, paste it into "
              "tmp/playground_token.txt, and run again within a few minutes.", file=sys.stderr)
        return 3
    (OUT / "playground").mkdir(parents=True, exist_ok=True)
    rows = []
    for n in range(1, a.runs + 1):
        r = c.post("/api/test/trigger", json={"kind": "flood", "action": "detected"}).json()
        iid = r.get("incident_id")
        if not iid:
            print(f"run {n}: trigger did not open an incident: {r}", file=sys.stderr)
            return 1
        got = wait(lambda: (d := c.get(f"/api/incidents/{iid}").json())["frames"] and d, timeout=90)
        if not got:
            print(f"run {n}: no frames within 90 s (token expired?)", file=sys.stderr)
        time.sleep(a.hold)
        c.post("/api/test/trigger", json={"kind": "flood", "action": "cleared"})
        wait(lambda: c.get(f"/api/incidents/{iid}").json().get("latest_pack"), timeout=120)
        pack = c.get(f"/api/incidents/{iid}/pack.json").json()
        (OUT / "playground" / f"{iid}.json").write_text(json.dumps(pack, indent=1, default=str), encoding="utf-8")
        st = pack["integrity"]["stats"]
        row = {"run": n, "incident_id": iid, "sensor_to_first_frame_s": st.get("sensor_to_first_frame_s"),
               "frames": st.get("frames"), "sessions_ok": st.get("sessions_ok"), "sessions_total": st.get("sessions_total"),
               "verdict": pack["integrity"]["verdict"]}
        rows.append(row)
        print(json.dumps(row))
        if n < a.runs:
            time.sleep(a.gap)

    vals = [r["sensor_to_first_frame_s"] for r in rows if r["sensor_to_first_frame_s"] is not None]
    summary = {
        "what": "seconds from a simulated flood sensor event to the first frame from Ring's Developer Playground "
                "doorbell, through the real Ring API (WHEP live view)",
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "n": len(rows), "with_frames": len(vals),
        "median_s": round(statistics.median(vals), 1) if vals else None,
        "min_s": min(vals) if vals else None, "max_s": max(vals) if vals else None,
        "runs": rows,
        "caveats": ["The sensor is simulated; the Playground has no sensors.",
                    "The first frame's time is when Watermark received it from the live session; Ring's own time is "
                    "burned into the image."],
    }
    (OUT / "playground-series.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("n", "with_frames", "median_s", "min_s", "max_s")}))
    return 0 if vals else 1


if __name__ == "__main__":
    sys.exit(main())
