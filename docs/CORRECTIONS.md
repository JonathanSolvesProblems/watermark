# Corrections log

Every placeholder or claim the data overruled, in order. Kept because a
correction that happened in public is worth more than a number that was right
the first time.

| Date | What the docs said | What the data said | Where fixed |
|---|---|---|---|
| 2026-09-15 | "Chime speaks: Water detected, water heater" (demo script v1) | A Ring Chime cannot speak text. Partner apps get two audio slots with pre-provisioned audio and can only trigger a slot. The room name moves to the push notification. | `docs/DEMO_SCRIPT.md`, `server/watermark/chime.py`, `docs/FRICTION_LOG.md` entry 6 |
| 2026-09-15 | Demo script v1 assumed frames could be pulled "on demand" | Image download never captures; a live session must be opened first (Ring calls this "the most common mistake"). | `server/watermark/capture.py` |
| 2026-10-08 | The first Playground run packs (commit 2ecf6ad) captioned real Ring frames of a bird feeder "Water visible: MOCK caption, synthetic frame, a blue band across the floor" | The mock captioner describes the synthetic mock frame and was still active outside mock mode because Bedrock is blocked on the account. Its text was false on a real Ring frame. It now runs only in mock mode; elsewhere a frame gets a Bedrock caption or "Not captioned". The five packs were rebuilt; every measured time is unchanged. | `server/watermark/captions.py`, `docs/runs/playground/`, test `test_no_mock_captions_outside_mock_mode` |
| 2026-10-08 | Each Playground pack's timeline listed the neighbouring runs' `flood_detected` and `flood_cleared` events | The pack gathered every event within a minute of the incident, and back-to-back runs are under a minute apart. Sensor wet/dry events now belong to an incident only between its opening and closing. | `server/watermark/pack.py` |
