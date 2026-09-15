"""Run the damage-findings pass (the RenoScout brain) over an incident's frames
for the pack's Aftermath section. Optional: if the brain package is not
installed, the section says so and the pack still builds."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("watermark.brain")


def analyze_frames(settings, blobs, frames: list[dict[str, Any]], max_frames: int = 6) -> dict[str, Any]:
    if not frames:
        return {"available": False, "reason": "no frames"}
    try:
        from watermark_brain.pipeline import analyze_paths
    except ImportError:
        return {"available": False, "reason": "brain package not installed"}
    # Spread the sample across the incident: first, last, and evenly between.
    idx = sorted({0, len(frames) - 1, *[int(i * (len(frames) - 1) / (max_frames - 1)) for i in range(max_frames)]})
    picked = [frames[i] for i in idx if 0 <= i < len(frames)]
    with tempfile.TemporaryDirectory() as td:
        paths = []
        for f in picked:
            p = Path(td) / f"frame-{f['id']}.jpg"
            try:
                p.write_bytes(blobs.get(f["path"]))
                paths.append(p)
            except Exception as e:  # noqa: BLE001
                log.debug("frame %s unreadable: %s", f["id"], e)
        if not paths:
            return {"available": False, "reason": "frames unreadable"}
        try:
            results = analyze_paths(paths, backend=settings.brain_backend, model=None,
                                    bedrock_region=settings.aws_region, cache_dir=Path(td) / ".cache")
        except Exception as e:  # noqa: BLE001
            return {"available": False, "reason": f"{type(e).__name__}: {e}"[:200]}
    findings = []
    for r in results:
        for fnd in r["analysis"].get("findings", []):
            if fnd.get("severity") == "none":
                continue
            findings.append({**fnd, "photo": r["photo"]})
    return {"available": True, "backend": settings.brain_backend, "frames_analyzed": len(results),
            "findings": findings}
