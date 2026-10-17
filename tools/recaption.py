"""Label already-recorded Ring frames with Amazon Rekognition and rebuild their packs.

The judged link replays real Ring Playground runs recorded before Rekognition was
wired in, so their frames were never captioned. This copies a data directory,
labels the same frames a live run would (first, last and every tenth of each
capture session), and rebuilds each incident's evidence pack in the copy. The
source directory is never touched.

    py tools/recaption.py --src server/data/playground-oct9 --dst server/data/replay-rek --profile watermark
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--profile", default="watermark")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--report", help="write a run record (labels per incident) to this JSON file")
    a = ap.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    if dst.exists():
        shutil.rmtree(dst)
    # Copy the -wal file too: a recorded run can live entirely in the write-ahead
    # log until SQLite checkpoints it, and the main file alone is then empty.
    shutil.copytree(src, dst)

    import boto3
    os.environ.update(MODE="playground", DATA_DIR=str(dst), BLOB_BACKEND="local", CAPTIONS_BACKEND="rekognition")
    from watermark.blobs import make_blob_store
    from watermark.captions import RekognitionCaptioner
    from watermark.config import Settings
    from watermark.db import Database
    from watermark.pack import PackBuilder

    settings = Settings.from_env()
    db, blobs = Database(settings.db_path), make_blob_store(settings)
    packs = PackBuilder(settings, db, blobs)
    cap = RekognitionCaptioner(a.region, client=boto3.Session(profile_name=a.profile).client("rekognition", region_name=a.region))

    report = []
    for inc in db.list_incidents():
        frames = db.frames_for_incident(inc["id"])
        by_session: dict[int, list[dict]] = {}
        for f in frames:
            by_session.setdefault(f["session_no"], []).append(f)
        labelled = 0
        for fs in by_session.values():
            for i, f in enumerate(fs):
                if not (i == 0 or i == len(fs) - 1 or i % 10 == 0):
                    continue
                c = cap.caption(blobs.get(f["path"]))
                db.execute("UPDATE frames SET caption=?, caption_model=?, water_visible=? WHERE id=?",
                           (c.description, c.model, None if c.water_visible is None else int(c.water_visible), f["id"]))
                labelled += 1
                report.append({"incident": inc["id"], "frame": f["id"], "labels": c.description,
                               "water_visible": c.water_visible})
        pack = packs.build(inc["id"])
        print(f"{inc['id']}: {labelled} of {len(frames)} frames labelled, claims "
              f"{pack['claims']['answered']} answered, {pack['claims']['partial']} partial")
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")   # one self-contained file to ship
    if not report:
        print("no frames found: check --src", file=sys.stderr)
        return 1
    if a.report:
        Path(a.report).write_text(json.dumps({"service": "Amazon Rekognition DetectLabels", "region": a.region,
                                              "source": str(src), "frames": report}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
