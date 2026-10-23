# Watermark

**When a Ring sensor finds water, Watermark makes the camera record it and proves it to your insurer.**

On June 20, 2026 the city sewer backed up into more than 60 units of my condo. Mine also came in
through the foundation, gaps beside the electrical panel and a basement window, one week
after I had finished rebuilding from my first flood (December 2025, a badly sloped drain
pipe and a toilet leak). The mitigation company's report said heavy rain, and floated my
backyard shed as the cause.
The only reason that didn't stick was two phone videos I took while it was happening,
because I happened to be home. Next time I won't be.

Watermark is a Ring Appstore app. A Ring Flood & Freeze sensor fires; the Ring Chime
plays; a Ring Indoor Cam that already sees the room opens a live session, which forces it
to record; frames with Ring's own time land until the sensor reads dry. A printed rover
that carries the Indoor Cam to a room no camera covers is the next step; its code and
AWS IoT Core dispatch are in the repo, but it is not part of this demo. What comes out is one evidence pack: timeline, frames, room
readings, device health, an **integrity section that lists every gap it could not
verify**, and a map against the questions my adjuster actually asked. It never states a
cause.

Built for the Ring track of [Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/),
with the AWS Builder and Open Source mini-challenges. MIT. The typed Ring Partner API
client it is built on is its own repo:
[ringwire](https://github.com/JonathanSolvesProblems/ringwire).

> Every number below traces to a committed run under `docs/runs/`.
> `py tools/check_claims.py` fails the build if the prose and the data disagree.

**Demo video (2:45):** https://www.youtube.com/watch?v=Ag496FBNvoE

**Live demo:** https://watermark.jonathansolvesproblems.com, a read-only replay of my recorded Ring Playground runs (real Ring frames with Ring's own timestamps).

## What it measures

- **Sensor to first frame, through the real Ring API:** the first Ring frame arrived 6.85 s after the sensor event, median of 10 runs, range 6.6 to 11.2 s (Ring Developer Playground, October 8 and 9, 2026). The camera is the Playground's doorbell reached through the real Ring API; the sensor is simulated, because Ring offers no sensors in the Playground and does not open device access to my account's region. Every pack is in `docs/runs/playground/`; `docs/runs/playground-series.json` is the summary.
- **My real claim's questions:** on one of those runs (`docs/runs/demo-run.json`, first frame in 6.9 s), the pack answers 2 of 7 questions my adjuster asked on my June 2026 claim and partly answers 2 more. The two it answers are when the water started and how long it stood, and where it was: the frames that would have settled whether it was sewer backup or clean rainwater, which decided which coverage limit applied. The other three are about the house and the policy, and are mine to answer. Cause is refused by design.
- **What Ring alone records:** with my real Flood & Freeze sensor in a bowl and my real Indoor Cam pointed at it, the Ring app alerts on the sensor, but its event history shows 0 motion recordings in the 3 minutes after the sensor reported water, because slowly rising water does not trip motion detection. That gap is what Watermark fills. (Filmed as a controlled test with real devices; the count is read from the Ring app's own event history.)
- **Captions:** the judged packs carry Amazon Rekognition labels on 5 frames per run (`docs/runs/rekognition-labels.json`). They describe what is in view and never claim a floor is dry. Prose captions from Amazon Bedrock are wired but AWS blocks Bedrock on my account.

## Run it in five minutes with nothing but Python and Node

```sh
py -m venv .venv
.venv\Scripts\python -m pip install -e sdk -e "server[dev]" -e brain -e "rover[dev]"
.venv\Scripts\python -m pytest                      # every test, no network needed

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
| `sdk/` | `ringwire`, a typed Python client for the Ring Partner API: devices, sensors, two-step media downloads, WHEP, chime playback, webhook HMAC, account-linking nonce. Also published on its own at `ringwire` for the Open Source challenge (see [docs/REPOS.md](docs/REPOS.md)) | 22 |
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

Amazon Rekognition labels what is in the captioned frames (`CAPTIONS_BACKEND=rekognition`),
and the flooring question in the claim map cites the floor material it names. It does not
judge wetness: on my June flood footage it labelled water on hardwood the same as the dry
floor, so it can add "water visible" but never "no water", and the sensor stays the record.
Bedrock (Converse API, Nova Lite) is wired for prose captions and the narrative, but AWS
blocks it on my account. AWS IoT Core carries dispatch commands to the rover as a Thing (measured with the drive
simulated on the Pi; the physical rover is the next step, not part of the demo).
S3 holds frames and packs. EC2 serves the judged link. Each is behind one environment
variable and defaults to a local mock.

## Honesty

- The demo flood is a controlled test: a real sensor in a bowl, water poured in slowly, labelled on
  screen and in the pack. Devices, timestamps and captures are real.
- Every frame carries Ring's timestamp; frames further than Ring's documented 10 s
  tolerance from the request are flagged. Events learned by polling rather than by
  webhook are flagged. Camera offline windows are reported as gaps.
- `docs/CORRECTIONS.md` lists every placeholder the data overruled.
- The rover is not in the demo: it has not yet passed `docs/ROVER_TRIALS.md` (4 of 5
  dispatches on the real floor), so nothing in the video or the fields claims it drives.

## Status

See `PHASE0.md` for the plan and the gates. Hardware and the real Ring account are the
next steps; everything above runs today in mock mode.
