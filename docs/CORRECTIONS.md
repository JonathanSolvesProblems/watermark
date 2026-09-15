# Corrections log

Every placeholder or claim the data overruled, in order. Kept because a
correction that happened in public is worth more than a number that was right
the first time.

| Date | What the docs said | What the data said | Where fixed |
|---|---|---|---|
| 2026-09-15 | "Chime speaks: Water detected, water heater" (demo script v1) | A Ring Chime cannot speak text. Partner apps get two audio slots with pre-provisioned audio and can only trigger a slot. The room name moves to the push notification. | `docs/DEMO_SCRIPT.md`, `server/watermark/chime.py`, `docs/FRICTION_LOG.md` entry 6 |
| 2026-09-15 | Demo script v1 assumed frames could be pulled "on demand" | Image download never captures; a live session must be opened first (Ring calls this "the most common mistake"). | `server/watermark/capture.py` |
