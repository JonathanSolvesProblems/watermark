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
When a Ring Flood & Freeze sensor fires, Watermark opens a live session on a Ring Indoor Cam that already sees the room (which forces it to record), and keeps pulling frames with Ring's own time until the sensor reads dry. It produces one evidence pack: timeline, frames, room readings, device health, an integrity section listing every gap it could not verify, and a map against the questions my adjuster actually asked on my real claim. It never states a cause. It can also sound the Ring Chime through the API, which the Ring app cannot do for a sensor; the Playground has no chime, so the demo does not show that part.

On June 20, 2026 the city sewer backed up into more than 60 units of my condo. Mine also came in through the foundation, gaps beside the electrical panel and a basement window, one week after I had rebuilt from my first flood. The mitigation report blamed heavy rain and floated my backyard shed. The only rebuttal was two phone videos I took because I happened to be home. Whether that water was sewer backup or clean rainwater decided which coverage limit applied. Watermark is what I wish had been running.

Measured through the real Ring API: the first Ring frame arrived 6.85 s after the sensor event, median of 10 runs, range 6.6 to 11.2 s. On one of those runs (first frame in 6.9 s), the pack answers 2 of 7 questions my adjuster asked and partly answers 2 more; the other 3 are about the house and the policy. With my real sensor in a bowl in front of my real Indoor Cam, the Ring app's event history shows 0 motion recordings in the 3 minutes after the sensor reported water: slowly rising water does not trip motion detection, and that is the gap Watermark fills.
```

## How it works (technical)

```
Ring Partner API surfaces the code uses: one-way account linking (HMAC nonce, app-integrations POST then PATCH), device discovery, status (sensor faulted state, reported_at, online), the Early Access sensor webhooks (flood_detected, flood_cleared, freeze_*, tamper_*), device_online/offline, WHEP live sessions (which force a recording), image download with X-Media-Timestamp and X-Media-Origin, event history, dynamic scopes (Cameras, Sensors, Chimes) and chime audio playback, the only write in the API.

Server: FastAPI, dogfooding the typed Python SDK `ringwire` I wrote for the Open Source challenge. Webhooks are persisted before anything else (Ring keeps no history for sensor events) and deduplicated on meta.request_id; a reconcile loop polls /status so a missed webhook can neither start nor end a capture silently, and events learned that way are marked so the pack can say which timestamps are Ring's.

Measured on Ring's Developer Playground: the camera is the Playground doorbell reached through the real API, and the sensor event is simulated, because the Playground has no sensors and Ring does not open device access to my region. Every pack says so on its first page.

Next, not in this demo: a printed rover that carries the Indoor Cam to a room no fixed camera covers (Raspberry Pi 4, printed 4WD chassis, line following with wet-floor, obstacle and end-of-line guards). Its code and its AWS IoT Core dispatch are in the repo; it has not yet driven on the floor, so the demo uses the fixed Indoor Cam only.

What existed before the hackathon: the rover's printed chassis and drive code and the photo-to-findings module (brain/) are adapted from my earlier RenoScout build. Everything else was written during the submission period: the Ring integration, the incident engine, the evidence pack and claim map, the ringwire client, the web app, the AWS integrations and the hosting.

Web: Next.js following the Ring UX design guide: passwordless account linking with email pre-fill, device list with online state, redirect to the Ring app for device settings, subscription status pointer to My Apps, a first-visit tutorial, and a complete data-deletion action.
```

## AWS Builder field

```
AWS IoT Core carries the dispatch for the next piece, a printed rover that brings the Indoor Cam to a room no fixed camera covers: the rover is a Thing (rover-1) with its own X.509 certificate and a least-privilege policy that only lets it receive its own command topic; the server publishes over MQTT with SigV4. Measured with the drive simulated on the Pi: a flood event reached it through IoT Core and it reported on station 7.7 s after the sensor (docs/runs/iot-dispatch.json; server/watermark/dispatch.py, rover/agent.py, tools/iot_setup.py). The physical rover is not part of the demo. Amazon S3 stores frames and evidence packs (server/watermark/blobs.py). The judged demo runs on Amazon EC2 (a Graviton t4g.small) as three systemd services that restart on failure and on reboot (tools/ec2_services.sh). Amazon Rekognition (DetectLabels) labels what is in each captioned Ring frame, and the pack's flooring question cites the floor material it names (server/watermark/captions.py, claimmap.py; 25 labelled frames across the 5 judged runs in docs/runs/rekognition-labels.json). I tested it on my own June flood footage first: it labels a film of water on hardwood exactly as it labels the dry floor, so in Watermark it can add a "water visible" but never a "no water"; the sensor stays the record of wetness. I designed captions for Amazon Bedrock (Nova Lite, code still in place), but AWS blocks Bedrock on my account with "Error 002" in every region I tried.
```

## Open Source field

```
Contribution URLs: https://github.com/AmazonAppDev/ring-api-helloworld/pull/44 (pull request to Amazon's Ring sample) and https://github.com/JonathanSolvesProblems/ringwire (new project, MIT, published to PyPI: https://pypi.org/project/ringwire/)
Project repository: https://github.com/JonathanSolvesProblems/watermark
GitHub username: JonathanSolvesProblems

What I did: two contributions. (1) ringwire, a new typed Python client for the Ring Partner API, built around the Early Access sensor scope: sensor status with flood, freeze, contact and tamper state, the sensor webhooks with HMAC verification, chime playback, WHEP live sessions, the two-step media downloads and the account-linking nonce. (2) A pull request to Amazon's own ring-api-helloworld adding sensor_status.py, the sample's first script that reads a sensor, in the sample's own style.

How it works: ringwire turns each JSON:API response into a typed object and encodes the traps in Ring's sensor docs, so callers cannot fall into them: the never-reported 1970 epoch becomes None, tamper reads `detected` rather than `faulted`, and `sensor_reporting_state` is never treated as liveness. Its tests run with no network. The PR script reads GET /v1/devices/{id}/status, prints every sensor attribute and reading, and auto-discovers a sensor by its status attributes, because the device list does not say which devices are sensors.

Why it matters: several Ring Partner API clients appeared during this hackathon, all built around doorbells and cameras, and Amazon's sample had no sensor code at all. Sensors are where Ring's Early Access is heading, and their docs carry three traps a newcomer meets on day one. ringwire is dogfooded: Watermark's server is built on it, and every one of its 10 measured Playground runs went through it.
```

## Built with

```
ring-partner-api, python, fastapi, next.js, typescript, aws-iot-core, amazon-s3, amazon-ec2, amazon-rekognition, webrtc, aiortc, raspberry-pi, openscad, sqlite
```

## Repo, video, feedback

```
Repo: https://github.com/JonathanSolvesProblems/watermark
Live demo: https://watermark.jonathansolvesproblems.com
Video: [URL]
```

## Notes (never pasted)

- **Two public repos, both MIT:** `watermark` (the submission) and `ringwire`
  (split from `sdk/` with `git subtree split`). Published 2026-10-15. PHASE0.md was removed
  from all history before publishing and is gitignored.
- **AWS field truth table (checked 2026-10-16):** IoT Core true (docs/runs/iot-dispatch.json).
  S3 true (packs in the bucket). EC2 true (instance i-0ef6aeb869c1fe94f serves the live link,
  survived a reboot in 26 s). Rekognition true (docs/runs/rekognition-labels.json, judged
  packs relabelled 2026-10-17 with tools/recaption.py). Bedrock still blocked in us-east-1,
  us-west-2, us-east-2 and ca-central-1 (last checked 2026-10-21, after Support called the case
  approved). Leave the field as written.
- **Teardown Dec 4:** `py tools/teardown.py --apply`, then revoke keys by hand (the script
  prints the list).
- **Open Source contribution:** PR #44 to AmazonAppDev/ring-api-helloworld (sensor_status.py),
  opened 2026-10-20, open and mergeable; ringwire 0.1.0 on PyPI.
- **The ablation count** comes from the Ring app's event history after the bowl test (22 October, 0 recordings),
  recorded in `docs/runs/ablation-run.json` as `ring_app_motion_events` with a screenshot.
- The tagline is 118 characters. Read it aloud once, logged out, on the live page, at T-48h.
- Product feedback and the friction log are separate fields; their sources are
  `docs/PRODUCT_FEEDBACK.md` and `docs/FRICTION_LOG.md`.
- Never mention the eligibility region, the address or the claim number in any field.
