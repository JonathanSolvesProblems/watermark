# Friction log

One entry per surprise, in the shape the submission form asks for: the task, the
steps, expected vs actual, severity, workaround, suggestion. Started on day one,
before any hardware arrived, from reading the Ring Partner API docs end to end.

Severity: **blocker** (could not proceed), **major** (hours lost or wrong design),
**minor** (minutes lost), **paper cut** (annoyance).

---

### 1. Image download never captures

- **Task:** get a frame from the camera the moment a flood sensor fires.
- **Steps:** read `POST /v1/devices/{id}/media/image/download`, planned to call it with the sensor event's timestamp.
- **Expected:** the endpoint would take a snapshot.
- **Actual:** it only reads existing recordings or periodic snapshots and returns `416 MEDIA_NOT_FOUND` otherwise. The docs call this "the most common mistake". The only way to force a recording is to open a live session (WHEP or RTSPS) first.
- **Severity:** major (it decides the whole capture design).
- **Workaround:** open a WHEP session, pull frames off the WebRTC track, then use image download as the fallback for the window the session covered.
- **Suggestion:** a `POST /media/image/capture` that triggers a snapshot on line-powered devices, or a `trigger_recording: true` option on the download endpoints. Failing that, put the warning at the top of the API reference table, not only on the endpoint page.

### 2. Sensor events have no history

- **Task:** recover a `flood_detected` webhook missed during a deploy.
- **Steps:** looked for sensor event types in `GET /v1/history/devices/{id}/events`.
- **Expected:** the same history endpoint cameras have.
- **Actual:** history returns `motion`, `on_demand` and `ding` only. Sensor events exist only in the webhook delivery and its 72-hour dead-letter queue, which needs a support request to replay.
- **Severity:** major.
- **Workaround:** persist every event on receipt before doing anything else; reconcile against `/status` every 60 s and mark those events `reconciled` so the evidence pack says which timestamps are Ring's and which are ours.
- **Suggestion:** include sensor event types in event history, or expose the dead-letter queue as a self-serve replay endpoint.

### 3. `reported_at` is the 1970 epoch for a device that never checked in

- **Task:** show "last seen" for each sensor.
- **Steps:** read `status.reported_at`.
- **Expected:** null for a device with no check-in.
- **Actual:** `1970-01-01T00:00:00Z`, which parses fine and silently reads as 56 years stale.
- **Severity:** minor.
- **Workaround:** the SDK maps the epoch to `None`.
- **Suggestion:** return `null`.

### 4. `sensor_reporting_state` reads `active` on a device that has never reported

- **Task:** decide whether a sensor is live.
- **Actual:** `sensor_reporting_state.value` is `active` regardless; only `online` and `reported_at` mean anything.
- **Severity:** minor.
- **Suggestion:** drop the field or make it reflect reporting.

### 5. The docs site does not render for tools

- **Task:** read the API reference programmatically.
- **Steps:** fetched `developer.amazon.com/docs/ring/api-documentation.html`.
- **Actual:** the sensor, media and auth sections do not appear in the fetched page; the content is only reachable through the Ring Appstore MCP server (`knowledge.appstore-mcp.ring.amazon.dev`), which works well once found.
- **Severity:** minor.
- **Workaround:** `tools/ringdocs.py` queries the MCP server directly.
- **Suggestion:** link the MCP server from the top of the documentation index, and publish the markdown sources.

### 6. A chime cannot say a room name

- **Task:** announce "Water detected, water heater" on the Ring Chime.
- **Steps:** read the chimes overview and the audio playback endpoint.
- **Expected:** text-to-speech, or at least uploading a clip per event at runtime.
- **Actual:** an app owns two fixed audio slots whose audio is provisioned outside the device API; playback only triggers a slot by `audio_ref`. No way to vary the audio by room.
- **Severity:** minor (design change, not a blocker).
- **Workaround:** slot 1 says "Water detected", slot 2 says "Freeze detected"; the room name goes in the push notification.
- **Suggestion:** allow more slots, or a short TTS string on the playback call.

### 7. Sensors are Early Access and cannot be published

- **Task:** plan a Ring Appstore listing.
- **Actual:** the Sensors scope works in sandbox and staging but "certification and publishing to Ring customers become available once it reaches general availability". No date given.
- **Severity:** major for the "beyond the hackathon" story, none for the demo.
- **Suggestion:** publish a target date for sensor GA.

### 8. Partner-initiated OAuth is invitation only

- **Task:** put a "Connect Ring" button in the web app.
- **Actual:** partner-initiated OAuth with PKCE is "available by invitation only"; the self-serve path is one-way linking from the Ring Appstore with the HMAC nonce.
- **Severity:** minor.
- **Workaround:** the app's home page tells the user to start from the Ring Appstore, and `/link` handles the nonce.

<!-- Add entries below as they happen. Date each one. -->
