# Product feedback (required field: every tool, API or SDK used)

The friction log (`docs/FRICTION_LOG.md`) holds the itemised issues, with steps and dates.

## Ring Partner API (Amazon Vision API)

- **Used for:** sensor webhooks, device status, live sessions, image download, chime playback, account linking.
- **Worked well:** the JSON:API shapes are consistent across device families, the webhook envelope is the same for every event, HMAC verification is documented with working code in three languages, the Playground gives a 30-minute token without registering an app, and the docs MCP server answers precise questions.
- **Needs work:** image and clip downloads that never capture (a live session is the only way to record now); no history for sensor events; the 1970 epoch for never-reported devices; no runtime way to vary chime audio; sensors stuck in Early Access with no GA date; partner-initiated OAuth by invitation only.
- **Onboarding:** reading the docs end to end took a morning and produced eight friction-log entries before any hardware arrived. The sensor pages are good once found; the HTML docs index does not surface them.
- **Would I build with it again:** yes. The API is small, honest about its limits, and the sandbox is real.

## Ring Appstore developer portal and Playground

- **Used for:** app registration, account linking, and every measured run (10 Playground runs, median 6.85 s from the sensor event to the first Ring frame).
- **Worked well:** the Playground is the only route that needs neither a US device nor an account link, and its live view streams real Ring video with Ring's own timestamp burned into every frame.
- **Needs work:** the portal's "Connect" only authorises visibility, so the real link has to happen through ring.com/appstore, which the portal never says. Device access is US-only, and a Canadian account links cleanly but then lists no devices, with no message explaining why. The Playground is not mentioned anywhere in the docs (I found it through another entrant's forum question). Its token lasts 30 minutes with no refresh, its camera goes offline about 16 minutes after a token is issued, and image download returns 403 there.
- **Suggestion:** link the Playground from the US-only notice, document which endpoints it supports, and say plainly in the app when a linked account has no eligible devices because of its region.
- **Onboarding:** registering the private app took minutes, and the Early Access sensor and chime scopes were selectable on a personal account. Getting to a first live frame took a day, because the Playground had to be found through the forum first; once found, a token and a live frame took about ten minutes.
- **Would I build with it again:** yes. The Playground is the reason this entry exists at all outside the US.

## Ring app

- **Used for:** setting up the real devices (Flood & Freeze sensor, Indoor Cam 2nd gen, Chime), linking my account to Watermark through ring.com, and the controlled test that shows what Ring records on its own.
- **Worked well:** the Flood & Freeze sensor paired over Amazon Sidewalk with no base station, and all three devices were set up the same evening they arrived.
- **Needs work:** the Appstore menu is missing from the Canadian Ring app (friction log 10), and the finding below.
- **Finding while testing with real devices:** a Ring Chime can be set to sound for camera motion, but not for a Flood & Freeze sensor. Under the Chime's Audio Settings, "Chime Alerts" lists only the Indoor Cam, and the Chime's own menu reads "Chime Alerts: Unavailable". A homeowner whose sensor detects water gets a phone notification and nothing in the house. Watermark plays the Chime through the API for exactly this reason.
- **Onboarding:** under an hour from unboxing to all three devices online.
- **Would I build with it again:** yes; it is what my customers already have.

## Amazon Bedrock (Converse API, Nova Lite)

- **Used for (designed):** frame captions and the pack narrative, plus the damage-findings pass.
- **Worked well:** nothing I could measure, because no call ever succeeded. The Converse API was quick to write against, and the image block plus a JSON-only instruction is all the captioner needs.
- **Needs work / what happened:** every call from my account returns "ValidationException Error 002: Access to Bedrock models is not allowed for this account". IAM was not the cause. A support case opened on Oct 7 was still unassigned on Oct 16, and at least two other entrants posted the same error on the hackathon forum, where the organisers had no escalation path.
- **Effect:** I moved frame labelling to Amazon Rekognition (below); the Bedrock path is ready and switches on with one setting. Still blocked on Oct 17 in us-east-1, us-west-2 and ca-central-1.
- **Suggestion:** for hackathons that hand out AWS credits, pre-clear Bedrock on participant accounts, or give the error a link to the specific review it is waiting on.
- **Onboarding:** blocked at the first call. The retired Model access page now says models enable on first invoke, so there was nothing left for me to switch on.
- **Would I build with it again:** yes, once the account is cleared; it is the right tool for prose captions. Not on a deadline without that clearance first.

## Amazon Rekognition (DetectLabels)

- **Used for:** labels on the captioned Ring frames, and the floor material for the adjuster's flooring question (`tools/recaption.py` relabelled the 5 judged runs; `docs/runs/rekognition-labels.json`).
- **Worked well:** no model access step, one IAM action (`rekognition:DetectLabels`), and it answered on the first call. On my June photos it named the floor "Hardwood" at 100%, which is exactly what my adjuster asked.
- **Needs work:** it cannot see shallow water. A film of water spreading across my hardwood on June 20 came back as "Floor 100%, Hardwood 100%, Stained Wood 100%", the same labels as the dry floor before the flood. For a flood product that means its silence is not evidence of dryness, so Watermark only lets it add a "water visible", never a "no water". It also labelled the Playground bird feeder "Hanukkah Menorah 73%" once; the pack shows that as it came, since the labels are model output.
- **Suggestion:** a "Wet surface" or "Standing water" label, or a short note in the label docs on what it does not detect, would save the next builder the test I had to run.
- **Onboarding:** from adding the IAM policy to the first labelled Ring frame took minutes.
- **Would I build with it again:** yes, for what is in the frame; not for whether a floor is wet.

## AWS IoT Core

- **Used for:** dispatch commands to the rover.
- **Worked well:** provisioning was quick from boto3: a Thing, an X.509 certificate and a least-privilege policy (connect as the rover, receive only its own command topic) in one script (`tools/iot_setup.py`). The server publishes with SigV4 over WebSockets, so it needs no certificate of its own. A flood event reached the rover and it reported on station 7.7 s after the sensor (`docs/runs/iot-dispatch.json`).
- **Needs work:** nothing blocked me; the dispatch worked on the first run.
- **Onboarding:** one script took me from nothing to a provisioned Thing and a first dispatch the same afternoon.
- **Would I build with it again:** yes. It is the cleanest way I have found to send a command to a device on a home network with no inbound port.

## Amazon EC2

- **Used for:** hosting the judged demo (a Graviton t4g.small) as systemd services; it came back by itself 26 s after a reboot.
- **Worked well:** a Graviton t4g.small runs the FastAPI server and the Next.js app together with 2 GB of swap for the build; first-boot setup is a short user-data script (`tools/ec2_userdata.sh`), and an Elastic IP lets my own subdomain point at it with a real certificate.
- **Needs work:** resolving the latest Amazon Linux image through the public SSM parameter needs `ssm:GetParameters`, which `AmazonEC2FullAccess` does not include, so I looked the image up with `describe-images` instead.
- **Onboarding:** launched from the CLI and serving the app in under an hour.
- **Would I build with it again:** yes, for a demo that has to stay up for a judging window.

## Amazon Devices Builder Tools / Ring MCP server

- **Used for:** documentation queries during the build (`tools/ringdocs.py`).
- **Worked well:** exact payload shapes, including fields the HTML docs hide.
- **Needs work:** discoverability; it should be linked from the docs index.
- **Onboarding:** one URL and no authentication; a 30-line script was enough to query it.
- **Would I build with it again:** yes; it answered questions the HTML docs could not, such as the sensor status shapes.

## Feature requests

| Request | Why it matters to Watermark | Priority |
|---|---|---|
| A capture endpoint (`POST /media/image/capture`), or `trigger_recording: true` on the download endpoints | Slow water does not trip motion, so there is often no recording to download when a flood sensor fires. Today the only way to make the camera record is to open a live session and pull frames off WebRTC. | Critical |
| Sensor events in event history, or a self-serve replay of the webhook dead-letter queue | A sensor event missed during a deploy is gone for good, and the evidence pack's first timestamp is the one an adjuster asks about. | Important |
| Chime alerts for sensors in the Ring app, and dynamic audio (or at least the room name) on chime playback | A flood sensor notifies a phone and nothing in the house; through the API the chime can only play a pre-provisioned slot. | Important |
| Device access outside the US, or a sensor simulator in the Developer Playground | Non-US developers cannot test a single sensor flow end to end; I had to simulate the sensor event and say so on every pack. | Important |
| A `null` `reported_at` for devices that never checked in, instead of the 1970 epoch | Every client has to special-case a value that parses as a real date. | Nice-to-have |