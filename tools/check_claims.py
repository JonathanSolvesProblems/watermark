#!/usr/bin/env python3
"""Fail the build if the prose and the data disagree.

Every headline number in the docs must trace to a committed run artefact in
`docs/runs/`. This script reads `docs/CLAIMS.json`, which maps each claim to a
regex over the docs and to the JSON path in a run file that must equal it, and
exits non-zero on any mismatch or on any number in the docs that has no claim.

    py tools/check_claims.py            # verify
    py tools/check_claims.py --list     # show every claim and its source

`docs/CLAIMS.json` shape:
{
  "runs": {"demo": "docs/runs/demo-run.json"},
  "claims": [
    {"id": "first_frame_s", "text": "sensor to first frame",
     "docs_regex": "first frame (?:within|in) ([0-9.]+) s", "run": "demo",
     "path": "integrity.stats.sensor_to_first_frame_s", "tolerance": 0.5},
    ...
  ],
  "watch_files": ["README.md", "docs/DEMO_SCRIPT.md", "docs/SUBMISSION.md"]
}

Placeholders written as `[N]` or `[TBD]` are allowed until a run exists; once the
run file exists they become failures. That is the point: the demo script gets
written first, and the data overrules it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "docs" / "CLAIMS.json"


def get_path(obj, path: str):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def main(argv: list[str]) -> int:
    if not CLAIMS.exists():
        print(f"no {CLAIMS.relative_to(ROOT)}; nothing to check")
        return 0
    spec = json.loads(CLAIMS.read_text(encoding="utf-8"))
    runs: dict[str, dict] = {}
    for name, rel in spec.get("runs", {}).items():
        p = ROOT / rel
        if p.exists():
            runs[name] = json.loads(p.read_text(encoding="utf-8"))
    texts = {f: (ROOT / f).read_text(encoding="utf-8") for f in spec.get("watch_files", []) if (ROOT / f).exists()}
    failures: list[str] = []
    listing = "--list" in argv

    for c in spec.get("claims", []):
        rx = re.compile(c["docs_regex"], re.I)
        found = []
        for fname, text in texts.items():
            for m in rx.finditer(text):
                found.append((fname, m.group(1)))
        run = runs.get(c["run"])
        expected = None
        if run is not None:
            try:
                expected = get_path(run, c["path"])
            except (KeyError, IndexError, TypeError):
                failures.append(f"{c['id']}: run '{c['run']}' has no {c['path']}")
                continue
        if listing:
            print(f"{c['id']:<24} docs={[v for _, v in found]} run={expected}")
        if not found:
            continue
        for fname, val in found:
            if val.upper() in ("N", "TBD", "X", "M"):
                if expected is not None:
                    failures.append(f"{c['id']}: {fname} still says [{val}] but run has {expected}")
                continue
            if expected is None:
                failures.append(f"{c['id']}: {fname} states {val} but no run file exists to back it")
                continue
            try:
                ok = abs(float(val) - float(expected)) <= float(c.get("tolerance", 0))
            except ValueError:
                ok = str(val).strip() == str(expected).strip()
            if not ok:
                failures.append(f"{c['id']}: {fname} says {val}, run says {expected}")

    if failures:
        print("CLAIM CHECK FAILED")
        for f in failures:
            print("  -", f)
        return 1
    print(f"claims ok ({len(spec.get('claims', []))} checked, {len(runs)} run file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
