# Submission fields

One field, one fenced block, nothing else inside a section. Commentary lives in the
Notes section at the bottom. Paste from the blocks only. Numbers in square brackets
are placeholders until `docs/runs/` exists and `py tools/check_claims.py` is green.

## Project name

```
Watermark
```

## Tagline

```
Ring already tells you the basement is flooding. Watermark drives a camera to it and proves it to your insurer.
```

## Tracks and mini challenges

```
Primary track: Ring
Mini challenges: AWS Builder, Open Source
```

## What it does

```
When a Ring Flood & Freeze sensor fires, Watermark plays the Ring Chime, sends a printed rover carrying a Ring Indoor Cam down a tape line to the room the sensor is in (or uses a fixed Indoor Cam that already sees it), opens a live session so the camera records, and pulls timestamped frames every few minutes until the sensor clears. It captions each frame with Amazon Bedrock, logs humidity from the rover's wand, and produces one evidence pack: timeline, frames with Ring's own media timestamps, drying curve, device health, an integrity section listing every gap it could not verify, and a map against the questions on a real insurance claim file. It never states a cause.

On June 20, 2026 the city sewer backed up into 52 units of my condo. The mitigation report blamed heavy rain and floated my backyard shed. The only rebuttal was two phone videos I took because I happened to be home. Watermark is what I wish had been running at 2 a.m.

Measured on a controlled test (real sensor, real water, real camera): first frame [N] s after the sensor, rover on station in [N] s, and the pack answers [N] of [M] questions on my real claim file. With the sensor scope switched off, the same test captured [N] frames.
```

## How it works (technical)

```
Ring Partner API surfaces in the judged path: one-way account linking (HMAC nonce, app-integrations POST then PATCH), device discovery, status (sensor faulted state, reported_at, online), the Early Access sensor webhooks (flood_detected, flood_cleared, freeze_*, tamper_*), device_online/offline, WHEP live sessions (which force a recording), image download with X-Media-Timestamp and X-Media-Origin, event history, dynamic scopes (Cameras, Sensors, Chimes) and chime audio playback, the only write in the API.

Server: FastAPI, dogfooding the typed Python SDK `ringpartner` I wrote for the Open Source challenge. Webhooks are persisted before anything else (Ring keeps no history for sensor events) and deduplicated on meta.request_id; a reconcile loop polls /status so a missed webhook can neither start nor end a capture silently, and events learned that way are marked so the pack can say which timestamps are Ring's.

AWS: Bedrock (Nova Lite, Converse API with image blocks) captions frames and writes the narrative; AWS IoT Core carries the dispatch to the rover as a Thing; S3 holds frames and packs.

Rover: Raspberry Pi 4 on a printed 4WD chassis, L298N, four TT motors, three TCRT5000 line sensors, an Arduino wand (DHT11, water sensor, HC-SR04). Bang-bang line following with three guards: wet floor (the destination), obstacle, end-of-line crossbar. Every judged frame comes from the Ring camera it carries; the Pi never captures evidence.

Web: Next.js following the Ring UX design guide: passwordless account linking, device list with online state, redirect to the Ring app for device settings, subscription status pointer to My Apps, and a complete data-deletion action that reaches S3.
```

## AWS Builder field

```
Amazon Bedrock (bedrock-runtime Converse API, amazon.nova-lite-v1:0) captions every frame and writes the pack narrative: server/watermark/captions.py and brain/watermark_brain/backends.py (BedrockBackend). AWS IoT Core (MQTT over the AWS IoT Device SDK v2) delivers dispatch commands to the rover as a Thing: server/watermark/dispatch.py (IoTDispatcher) and rover/agent.py (IoTCommands). Amazon S3 stores frames and packs: server/watermark/blobs.py (S3BlobStore).
```

## Open Source field

```
New project: ringpartner, a typed Python client for the Ring Partner API (devices, sensors, two-step media downloads, WHEP sessions, chime playback, webhook HMAC verification, account-linking nonce). MIT. Repo: [URL]. Contribution: PR to AmazonAppDev/ring-api-helloworld adding the sensor webhook event types to its normaliser, with tests. PR: [URL]. GitHub: JonathanSolvesProblems. Why it matters: the official sample predates the Early Access sensor scope, and no typed client for the official API existed; every Ring Appstore developer who touches sensors re-reads the same docs I did.
```

## Repo, video, feedback

```
Repo: [URL]
Video: [URL]
```

## Notes (never pasted)

- The tagline is 111 characters. Read it aloud once, logged out, on the live page, at T-48h.
- "[N]" placeholders are enforced by `tools/check_claims.py`. Do not hand-edit numbers; copy the run file.
- Product feedback and the friction log are separate fields; their sources are `docs/PRODUCT_FEEDBACK.md` and `docs/FRICTION_LOG.md`.
- If the rover fails the Sept 26 gate, delete "sends a printed rover ... or" from "What it does" and lead with the fixed camera.
