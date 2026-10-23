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

### 9. "Connect Ring account" in the portal does not link the account

- **Task:** link my own Ring account to my private app, per the private-app FAQ ("Click Log in with Ring ... Ring sends an authorization code to your Token Exchange URL").
- **Steps:** Developer Portal → Watermark → Connect → Connect Ring account, signed in with my Ring account. The portal then listed the account as connected.
- **Expected:** a POST to the Token Exchange URL and a redirect to the Account Link URL.
- **Actual:** nothing reached either URL (tunnel request log shows no call). Ring app → Control Center → Linked Accounts said "You have no linked accounts." The portal step only made the app visible to that account. The real link only happened after I opened ring.com/appstore, found Watermark and pressed Connect App, at which point the token exchange, the nonce redirect and the `app_integration_added` webhook all arrived within 25 seconds.
- **Severity:** major (an hour of looking for a bug in my own token handler).
- **Workaround:** after the portal Connect step, install the app from ring.com/appstore.
- **Suggestion:** rename the button to "Authorize account to see this app", and say on that page and in FAQ Q10 that the account owner then installs it from the Ring Appstore.

### 10. The Ring Appstore is missing from the Canadian Ring app

- **Task:** install my private app from the Ring app, as the support article describes (menu → Apps → Explore Ring Appstore).
- **Steps:** Ring app 3.114.0 on Android, Canadian account, primary owner, Pro trial active, camera online.
- **Expected:** an Apps entry in the menu (the docs say private apps bypass location eligibility).
- **Actual:** no Apps entry, before or after a force restart. ring.com/appstore in a desktop browser worked.
- **Severity:** minor once found.
- **Workaround:** use ring.com/appstore.
- **Suggestion:** show Apps in the mobile menu whenever the account has a connected private app, regardless of country.

### 11. Linked, but `/v1/devices` returns an empty list

- **Task:** discover devices right after linking.
- **Steps:** link completed (POST and PATCH app-integrations succeeded, `app_integration_added` received), then `GET /v1/devices`.
- **Expected:** the camera, chime and flood sensor on the account.
- **Actual:** `{"data": []}`. The `app_integration_added` payload carries no device list, so there is no way to tell from the partner side whether the user skipped device selection or consents are still activating. `GET /v1/accounts/me/app-integrations` returns 403, so the integration's state cannot be read back either.
- **Cause found:** ring.com → My apps → Watermark showed "Inactive. Needs attention. No locations are connected." Pressing **Add Location** returned "There are currently no eligible locations available for subscription. We cannot sign you up for this service." The account is the primary owner, the location has a camera, chime and flood sensor online, and a Ring Pro trial started that day. The private-app FAQ (Q12, Q13) says a trial is accepted and private apps bypass location eligibility, so either the trial is not counted yet or the web Appstore applies the public-app eligibility check to a private app.
- **Root cause (as far as the docs say):** the Test page of the developer guide carries a warning, "Only US Located Devices: Currently we only support devices located in the US." My location is in Canada. Disconnecting and reconnecting in the portal re-used the existing link without ever showing a location or device picker, and Add Location returned the same message. This contradicts the private-app FAQ (Q13: "Private apps bypass all location eligibility checks. Connected accounts can access the app regardless of their country or state").
- **Severity:** blocker for any developer outside the US, in a hackathon advertised globally. Every step before device access works (token exchange, nonce link, signed webhooks), so the failure appears only after a developer has bought devices and a subscription.
- **Workaround:** pending a reply from Ring DevRel.
- **Suggestion:** resolve the contradiction in the docs; state the US-only restriction on the private-app page, the hackathon page and the Add Location error itself ("Watermark can only connect to locations in the US" rather than "no eligible locations available for subscription"); and either honour Q13 for private apps or offer non-US developers a sandbox account with test devices.
- **Suggestion:** include the consented device ids (or a count) in `app_integration_added`, and allow GET on app-integrations so a partner can show "0 devices shared, go back and pick some."

### 12. The Developer Playground is the only path outside the US, and the docs never mention it

- **Task:** find a supported way to build the Ring track from Canada after device access was refused (entry 11).
- **Steps:** searched the Ring docs MCP server for "Playground", "sandbox", "simulator" and "test devices"; read the private-app FAQ and the Test guide.
- **Expected:** a pointer from the "Only US Located Devices" warning to the alternative.
- **Actual:** no document mentions the Playground. I learned it exists from another entrant's question on the Devpost forum, answered by Ring DevRel ("the Playground is the only documented route that needs neither a US device nor an account link"). It lives in the developer console: a 30-minute OAuth token, one simulated DoorbellPro, and three live-view streams (Package, Vehicle, Motion).
- **Severity:** major (a day spent on real-device linking that could never work from Canada).
- **Workaround:** the Playground token, used by the same SDK and server code that the real account uses.
- **Suggestion:** link the Playground from the US-only warning, the private-app FAQ and the hackathon page, and index it in the docs MCP server.

### 13. Playground: live view works, image download is 403

- **Task:** grab a still at a timestamp, the fallback when a live session is too short.
- **Steps:** `GET /v1/devices/{id}/media/image/download?at_timestamp=...` with the Playground token, before and after a live session.
- **Expected:** a 303 to a presigned image, or 416 if nothing was recorded.
- **Actual:** 403. The token's only scope is `ava.v1:read`. A WHEP session on the same token returned 9 frames in 15 seconds, with Ring's timestamp burned into each frame.
- **Severity:** minor.
- **Workaround:** capture from the WHEP track only; disable the download fallback in Playground mode.
- **Suggestion:** grant the media download scope to Playground tokens, or document which endpoints the Playground supports.

### 14. Playground token lasts 30 minutes with no refresh

- **Task:** keep a server running against the Playground for a demo session.
- **Expected:** a refresh token, like a linked account.
- **Actual:** a bare access token that expires in 30 minutes; "Closing this tab will clear the token."
- **Severity:** paper cut.
- **Workaround:** the server reads the token from a file and reports clearly when it has expired, so a fresh one can be pasted in.
- **Suggestion:** issue Playground tokens with a refresh token, or a longer life for hackathon participants.

### 15. The Playground camera goes offline about 16 minutes after a token is issued

- **Task:** run five measured incidents in a row against the Playground doorbell.
- **Steps:** generated a token at 16:30:44 UTC; live view worked at 16:32 and 16:35; a series started at 16:49 found the camera offline.
- **Expected:** a simulated device that stays online while the token is valid (30 minutes).
- **Actual:** `GET /status` reported `online: false` with `reported_at` 16:46:43, exactly 16 minutes after the token was issued. A WHEP session against the offline device is still accepted (201) but streams no media. A new token cannot be generated until the old one has expired, so the device stays offline for the last half of every token.
- **Severity:** minor (cost one measurement series; Watermark correctly refused to record from an offline camera).
- **Workaround:** run measurements in the first 15 minutes after generating a token; the run script checks the camera is online before it starts.
- **Suggestion:** keep the Playground device online for the token's whole life, or say in the console how long it stays online.

### 16. A flood sensor in a rounded bowl never reports water

- **Task:** the controlled test for the demo: the Flood & Freeze sensor in a bowl, water poured in slowly, with the Indoor Cam watching and the phone screen recorded.
- **Steps:** set the sensor in a rounded cereal bowl, poured water until it sat in a few millimetres, waited seven minutes while polling the phone's notifications.
- **Expected:** a flood alert within a minute or so.
- **Actual:** nothing, from the sensor or the app. The sensor had tilted on the curved bottom, so only one of the two contacts was in the water. The app showed it Online with Good signal the whole time and gave no hint. Dried the contacts, restarted it (two green blinks), set it flat in a dish, poured again: the alert reached the phone within 36 s of my starting to pour (20:35:10).
- **Severity:** minor for me (cost ten minutes), but a homeowner who tests the sensor once in a sink and sees nothing may conclude it is broken.
- **Workaround:** a flat surface, and Ring's own test instructions: water must touch both contacts at the same time.
- **Suggestion:** say "both contacts" and "flat, contacts down" on the setup screen where the app suggests testing with a little water, and show the last water-detected time on the device page so a silent test is visibly a non-event rather than ambiguous.
