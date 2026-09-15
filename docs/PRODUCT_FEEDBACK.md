# Product feedback (required field: every tool, API or SDK used)

Draft. Update as the build goes; the friction log holds the itemised issues.

## Ring Partner API (Amazon Vision API)

- **Used for:** sensor webhooks, device status, live sessions, image download, chime playback, account linking.
- **Worked well:** the JSON:API shapes are consistent across device families, the webhook envelope is the same for every event, HMAC verification is documented with working code in three languages, the Playground gives a 30-minute token without registering an app, and the docs MCP server answers precise questions.
- **Needs work:** image and clip downloads that never capture (a live session is the only way to record now); no history for sensor events; the 1970 epoch for never-reported devices; no runtime way to vary chime audio; sensors stuck in Early Access with no GA date; partner-initiated OAuth by invitation only.
- **Onboarding:** reading the docs end to end took a morning and produced eight friction-log entries before any hardware arrived. The sensor pages are good once found; the HTML docs index does not surface them.
- **Would I build with it again:** yes. The API is small, honest about its limits, and the sandbox is real.

## Ring Appstore developer portal and Playground

- **Used for:** app registration, staging users, tokens.
- [fill in after registration]

## Amazon Bedrock (Converse API, Nova Lite)

- **Used for:** frame captions and the pack narrative, plus the damage-findings pass.
- [fill in after first live captions: latency, cost per incident, caption quality on real frames]

## AWS IoT Core

- **Used for:** dispatch commands to the rover.
- [fill in after the Thing is provisioned]

## Amazon Devices Builder Tools / Ring MCP server

- **Used for:** documentation queries during the build (`tools/ringdocs.py`).
- **Worked well:** exact payload shapes, including fields the HTML docs hide.
- **Needs work:** discoverability; it should be linked from the docs index.
