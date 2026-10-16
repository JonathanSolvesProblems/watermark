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

## Ring app

- **Finding while testing with real devices:** a Ring Chime can be set to sound for camera motion, but not for a Flood & Freeze sensor. Under the Chime's Audio Settings, "Chime Alerts" lists only the Indoor Cam, and the Chime's own menu reads "Chime Alerts: Unavailable". A homeowner whose sensor detects water gets a phone notification and nothing in the house. Watermark plays the Chime through the API for exactly this reason.

## Amazon Bedrock (Converse API, Nova Lite)

- **Used for (designed):** frame captions and the pack narrative, plus the damage-findings pass.
- **What happened:** every call from my account returns "ValidationException Error 002: Access to Bedrock models is not allowed for this account". IAM was not the cause. A support case opened on Oct 7 was still unassigned on Oct 16, and at least two other entrants posted the same error on the hackathon forum, where the organisers had no escalation path.
- **Effect:** the measured packs carry no captions and say so; the code path is ready and switches on with one setting.
- **Suggestion:** for hackathons that hand out AWS credits, pre-clear Bedrock on participant accounts, or give the error a link to the specific review it is waiting on.

## AWS IoT Core

- **Used for:** dispatch commands to the rover.
- **Worked well:** provisioning was quick from boto3: a Thing, an X.509 certificate and a least-privilege policy (connect as the rover, receive only its own command topic) in one script (`tools/iot_setup.py`). The server publishes with SigV4 over WebSockets, so it needs no certificate of its own. A flood event reached the rover and it reported on station 7.7 s after the sensor (`docs/runs/iot-dispatch.json`).
- **Needs work:** nothing blocked me; the dispatch worked on the first run.

## Amazon EC2

- **Used for:** hosting the judged demo (a Graviton t4g.small) as systemd services; it came back by itself 26 s after a reboot.
- **Note:** resolving the latest Amazon Linux image through the public SSM parameter needs `ssm:GetParameters`, which `AmazonEC2FullAccess` does not include, so I looked the image up with `describe-images` instead.

## Amazon Devices Builder Tools / Ring MCP server

- **Used for:** documentation queries during the build (`tools/ringdocs.py`).
- **Worked well:** exact payload shapes, including fields the HTML docs hide.
- **Needs work:** discoverability; it should be linked from the docs index.
