# Submission fields

One field, one fenced block, nothing else inside a section. Commentary lives in the
Notes section at the bottom. Paste from the blocks only. Every number traces to
`docs/runs/` and `py tools/check_claims.py` must be green before pasting.

## Project name

```
Watermark
```

## Tagline

```
Ring already tells you the basement is flooding. Watermark points a camera at the water and proves it to your insurer.
```

## Tracks and mini challenges

```
Primary track: Ring
Mini challenges: AWS Builder, Open Source
```

## What it does

```
When a Ring Flood & Freeze sensor fires, Watermark plays the Ring Chime, opens a live session on a Ring Indoor Cam that already sees the room (which forces it to record), and keeps pulling frames with Ring's own time until the sensor reads dry. It produces one evidence pack: timeline, frames, room readings, device health, an integrity section listing every gap it could not verify, and a map against the questions my adjuster actually asked on my real claim. It never states a cause. A printed rover that carries the Indoor Cam down a tape line to the room is in progress.

On June 20, 2026 the city sewer backed up into more than 60 units of my condo. Mine also came in through the foundation, gaps beside the electrical panel and a basement window, one week after I had rebuilt from my first flood. The mitigation report blamed heavy rain and floated my backyard shed. The only rebuttal was two phone videos I took because I happened to be home. Whether that water was sewer backup or clean rainwater decided which coverage limit applied. Watermark is what I wish had been running.

Measured through the real Ring API: the first Ring frame arrived 6.85 s after the sensor event, median of 10 runs, range 6.6 to 11.2 s. On one of those runs (first frame in 6.9 s), the pack answers 2 of 7 questions my adjuster asked and partly answers 2 more; the other 3 are about the house and the policy. With my real sensor in a tray in front of my real Indoor Cam, the Ring app's event history shows [N] motion recordings while the tray filled: slowly rising water does not trip motion detection, and that is the gap Watermark fills.
```

## How it works (technical)

```
Ring Partner API surfaces in the judged path: one-way account linking (HMAC nonce, app-integrations POST then PATCH), device discovery, status (sensor faulted state, reported_at, online), the Early Access sensor webhooks (flood_detected, flood_cleared, freeze_*, tamper_*), device_online/offline, WHEP live sessions (which force a recording), image download with X-Media-Timestamp and X-Media-Origin, event history, dynamic scopes (Cameras, Sensors, Chimes) and chime audio playback, the only write in the API.

Server: FastAPI, dogfooding the typed Python SDK `ringpartner` I wrote for the Open Source challenge. Webhooks are persisted before anything else (Ring keeps no history for sensor events) and deduplicated on meta.request_id; a reconcile loop polls /status so a missed webhook can neither start nor end a capture silently, and events learned that way are marked so the pack can say which timestamps are Ring's.

Measured on Ring's Developer Playground: the camera is the Playground doorbell reached through the real API, and the sensor event is simulated, because the Playground has no sensors and Ring does not open device access to my region. Every pack says so on its first page.

Rover (in progress): Raspberry Pi 4 on a printed 4WD chassis, L298N, four TT motors, three TCRT5000 line sensors, an Arduino wand (DHT11, water sensor, HC-SR04). Bang-bang line following with three guards: wet floor (the destination), obstacle, end-of-line crossbar. It runs on the Pi today and reaches its station in simulation; every judged frame comes from the Ring camera it carries, never from the Pi.

Web: Next.js following the Ring UX design guide: passwordless account linking with email pre-fill, device list with online state, redirect to the Ring app for device settings, subscription status pointer to My Apps, a first-visit tutorial, and a complete data-deletion action.
```

## AWS Builder field

```
AWS IoT Core delivers the dispatch to the rover: the rover is a Thing (rover-1) with its own X.509 certificate and a least-privilege policy that only lets it receive its own command topic; the server publishes over MQTT with SigV4. Measured: a flood event reached the rover through IoT Core and it reported on station 7.7 s after the sensor (docs/runs/iot-dispatch.json; server/watermark/dispatch.py, rover/agent.py, tools/iot_setup.py). Amazon S3 stores frames and evidence packs (server/watermark/blobs.py). The judged demo runs on Amazon EC2 (a Graviton t4g.small) as three systemd services that restart on failure and on reboot (tools/ec2_services.sh). Amazon Rekognition (DetectLabels) labels what is in each captioned Ring frame, and the pack's flooring question cites the floor material it names (server/watermark/captions.py, claimmap.py; 25 labelled frames across the 5 judged runs in docs/runs/rekognition-labels.json). I tested it on my own June flood footage first: it labels a film of water on hardwood exactly as it labels the dry floor, so in Watermark it can add a "water visible" but never a "no water"; the sensor stays the record of wetness. I designed captions for Amazon Bedrock (Nova Lite, code still in place), but AWS blocks Bedrock on my account with "Error 002" in every region I tried.
```

## Open Source field

```
New project: ringpartner, a typed Python client for the Ring Partner API (devices, sensors, two-step media downloads, WHEP sessions, chime playback, webhook HMAC verification, account-linking nonce). MIT. Repo: https://github.com/JonathanSolvesProblems/ring-partner-py. Watermark's server is built on it. GitHub: JonathanSolvesProblems. Why it matters: no typed client for the official Ring Partner API existed, and the Early Access sensor scope is newer than the official sample; every Ring Appstore developer who touches sensors re-reads the same docs I did.
```

## Repo, video, feedback

```
Repo: https://github.com/JonathanSolvesProblems/watermark
Live demo: https://pendant-entourage-supper.ngrok-free.dev
Video: [URL]
```

## Notes (never pasted)

- **Two public repos, both MIT:** `watermark` (the submission) and `ring-partner-py`
  (split from `sdk/` with `git subtree split`). Published 2026-10-15. PHASE0.md was removed
  from all history before publishing and is gitignored.
- **AWS field truth table (checked 2026-10-16):** IoT Core true (docs/runs/iot-dispatch.json).
  S3 true (packs in the bucket). EC2 true (instance i-0ef6aeb869c1fe94f serves the live link,
  survived a reboot in 26 s). Rekognition true (docs/runs/rekognition-labels.json, judged
  packs relabelled 2026-10-17 with tools/recaption.py). Bedrock still blocked in us-east-1,
  us-west-2 and ca-central-1 (checked 2026-10-17): if it is unblocked by Oct 20, run
  captions on a Playground pack with CAPTIONS_BACKEND=bedrock and drop the "blocks" clause.
- **Teardown Dec 4:** `py tools/teardown.py --apply`, then revoke keys by hand (the script
  prints the list).
- **Open Source contribution:** the PR to AmazonAppDev/ring-api-helloworld (sensor webhook
  types in its normaliser) is not opened. Either open it by Oct 20 and add "Contribution:
  PR <URL>" to the field, or leave the field as the new project only.
- **The ablation count** comes from the Ring app's event history after the tray test,
  recorded in `docs/runs/ablation-run.json` as `ring_app_motion_events` with a screenshot.
- The tagline is 115 characters. Read it aloud once, logged out, on the live page, at T-48h.
- Product feedback and the friction log are separate fields; their sources are
  `docs/PRODUCT_FEEDBACK.md` and `docs/FRICTION_LOG.md`.
- Never mention the eligibility region, the address or the claim number in any field.
