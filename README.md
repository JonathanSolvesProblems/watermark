# Watermark

**When a Ring sensor finds water, the camera goes to the water.**

On June 20, 2026 the city sewer backed up into 52 units of my condo, mine included. The
mitigation company's report said heavy rain, and floated my backyard shed as the cause.
The only reason that didn't stick was two phone videos I took while it was happening,
because I happened to be home. Next time I won't be.

Watermark is a Ring Appstore app. A Ring Flood & Freeze sensor fires; the Ring Chime
plays; a printed rover carrying a Ring Indoor Cam follows a tape line to the room (or a
fixed Indoor Cam that already sees it takes over); a live session forces the camera to
record; frames with Ring's own timestamps land every few minutes until the sensor
clears. What comes out is one evidence pack: timeline, frames with captions, humidity,
device health, an **integrity section that lists every gap it could not verify**, and a
map against the questions on a real insurance claim file. It never states a cause.

Built for the Ring track of [Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/),
with the AWS Builder and Open Source mini-challenges. MIT.

> Numbers in this README and in `docs/` are placeholders until a real run is committed
> under `docs/runs/`. `py tools/check_claims.py` fails the build if the prose and the data
> disagree.

## What it measures

- **Measured on Ring's Developer Playground (October 8, 2026):** the first Ring frame arrived 6.7 s after the sensor event, median of 5 runs, range 6.6 to 7.1 s. The camera is the Playground's doorbell reached through the real Ring API; the sensor is simulated, because Ring offers no sensors in the Playground and limits real device access to US locations. Every run's evidence pack is in `docs/runs/playground/`, and `docs/runs/playground-series.json` is the summary.
- **Sensor to first frame:** first frame at [N] s after the sensor event, graded by Ring's own `X-Media-Timestamp`.
- **Rover on station in [N] s** after the sensor, graded by the rover's report against the sensor timestamp.
- **Claim questions:** the pack answers [N] of [M] questions on my real claim file. Cause is refused by design.
- **Ablation:** same controlled test with the sensor scope off captured [N] frames, because rising water does not trip motion detection. That number is what Ring's sensor contributes.

## Run it in five minutes with nothing but Python and Node

```sh
py -m venv .venv
.venv\Scripts\pip install -e sdk -e "server[dev]" -e brain -e "rover[dev]"
.venv\Scripts\python -m pytest                      # 48 tests, no network

cd server && set MODE=mock && ..\.venv\Scripts\python -m uvicorn watermark.main:app --port 8765
cd web && npm install && set NEXT_PUBLIC_API_URL=http://localhost:8765 && npm run build && npm start
```

Open http://localhost:3000/dashboard and press **Simulate: sensor wet**. In mock mode the
server has a linked account with one flood sensor routed to a rover camera, a fixed camera,
and a chime; the rover can be a laptop:

```sh
set ROVER_SIMULATE=1 && set WATERMARK_SERVER=http://localhost:8765 && .venv\Scripts\python -m rover.agent
```

The mock frames are grey rooms with a blue band stamped MOCK. They exist so the pipeline
can be exercised end to end; every judged frame in the demo comes from a real Ring camera.

## Layout

| Folder | What | Tests |
|---|---|---|
| `sdk/` | `ringpartner`, a typed Python client for the Ring Partner API: devices, sensors, two-step media downloads, WHEP, chime playback, webhook HMAC, account-linking nonce. Also published on its own at `ring-partner-py` for the Open Source challenge (see [docs/REPOS.md](docs/REPOS.md)) | 22 |
| `server/` | FastAPI: webhook receiver (persist first, dedupe on `request_id`), incident state machine, reconcile loop, capture (WHEP via aiortc, download fallback), Bedrock captions, rover dispatch (local or AWS IoT Core), evidence pack (HTML, JSON, PDF) | 14 |
| `rover/` | Raspberry Pi 4 on the printed 4WD chassis: line following with wet, blocked and end-of-line guards; the wand; the dispatch agent | 9 |
| `brain/` | Photos of a wet room to adjuster-style findings (from RenoScout, verified on the June photos), with a Bedrock backend | 3 |
| `hardware/` | OpenSCAD for the chassis, riser, wand and the new Ring Indoor Cam cradle; all print support-free | |
| `web/` | Next.js app following the Ring UX design guide: passwordless link, dashboard, incident, setup, deletion | build |
| `docs/` | Demo script, friction log, product feedback, submission fields, rover trials, corrections | |
| `tools/` | `ringdocs.py` (queries Ring's docs MCP server), `check_claims.py` | |

## Ring surfaces in the judged path

Account linking (one-way, HMAC nonce, app-integrations POST then PATCH) · device
discovery · status (`flood_detection.faulted`, `reported_at`, `online`) · the Early Access
sensor webhooks (`flood_detected`, `flood_cleared`, `freeze_*`, `tamper_*`) ·
`device_online` / `device_offline` · WHEP live sessions (the only way to make a camera
record on demand) · image download with `X-Media-Timestamp` and `X-Media-Origin` ·
event history · dynamic scopes (Cameras, Sensors, Chimes) · chime audio playback, the
only write in the whole API.

Three things the docs say that shaped the design: the download endpoints never capture,
sensor events have no history, and a chime cannot say a room name. All eight surprises
so far are in `docs/FRICTION_LOG.md`.

## AWS

Bedrock (Converse API, Nova Lite) captions every frame and writes the narrative. AWS IoT
Core carries dispatch commands to the rover as a Thing. S3 holds frames and packs. All
three are behind one environment variable each and default to local mocks.

## Honesty

- The demo flood is a controlled test: a real sensor lowered into a tray, labelled on
  screen and in the pack. Devices, timestamps and captures are real.
- Every frame carries Ring's timestamp; frames further than Ring's documented 10 s
  tolerance from the request are flagged. Events learned by polling rather than by
  webhook are flagged. Camera offline windows are reported as gaps.
- `docs/CORRECTIONS.md` lists every placeholder the data overruled.
- The rover is in the demo only if it passes `docs/ROVER_TRIALS.md` (4 of 5 dispatches).

## Status

See `PHASE0.md` for the plan and the gates. Hardware and the real Ring account are the
next steps; everything above runs today in mock mode.
