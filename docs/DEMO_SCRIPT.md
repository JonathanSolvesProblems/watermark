# Demo script (v3, after the first measured runs)

Target about 110 seconds, spoken at an easy pace. Every number on screen comes from
`docs/runs/playground-series.json`; `py tools/check_claims.py` fails if this file and
the run data disagree. Narration is in plain text; what is on screen is in brackets.
Screen clips are in `demo/broll/` (made by `tools/record_broll.py`); hardware shots are
filmed by me and listed at the bottom.

## Script

**0:00 The flood**
[H1: stills from my two June 20 videos, address blurred]

> On June 20th the city sewer backed up into fifty-two units of my condo. Mine came in
> through the foundation and a basement window too, one week after I'd rebuilt from my
> first flood. The mitigation report blamed the rain, and my backyard shed. What stopped
> that was two phone videos I happened to take. Next time, I might not be home.

**0:15 The idea**
[H2: my real Flood & Freeze sensor going into a tray of water, label on screen:
"Controlled test. Real device."]

> So I built Watermark. A Ring flood sensor knows the moment water arrives. Watermark
> turns that moment into evidence: a Ring camera records, and it all lands in one pack for
> my insurer.

**0:27 The real alert**
[H3: my phone, the Ring app's flood alert arriving]

> That's Ring telling me, on my phone. What Ring doesn't do is film it. A slow puddle
> doesn't trip motion detection.

[H5: the Ring app's event history for the Indoor Cam over the same minutes, showing what
it did and did not record]

**0:37 The honest part**
[Screen: 01-dashboard.webm, the hatched Playground notice in view]

> One honest note: Ring only opens real devices to partner apps in the US, and I'm in
> Canada. So here the camera is Ring's Developer Playground, through the real Ring API,
> and the sensor event is simulated. Every page says so.

**0:52 The measurement**
[Screen: 02-incident-gauge.webm. On screen: "The first Ring frame arrived 6.7 s after the
sensor event, median of 5 runs, range 6.6 to 7.1 s."]

> The sensor fires, Watermark opens a live session, and the first Ring frame is in hand in
> under seven seconds. Five runs, median six point seven. The pink bar is how long the water
> stood; each notch is a frame.

**1:08 The frames**
[Screen: 03-incident-frames.webm, Ring's own timestamp burned into every frame]

> These are Ring's frames, with Ring's own time stamped in. Ring's test camera watches a
> bird feeder, not my basement, so instead of guessing about water, the page says "not
> captioned".

**1:20 What it won't claim**
[Screen: 04-incident-integrity.webm, then 05-pack.webm]

> Every pack lists what it can't vouch for, like a simulated sensor or a camera that went
> offline, and it never states a cause. That's the adjuster's call. The timeline is mine.

**1:34 Close**
[H6: the sensor, the Indoor Cam and the Chime on a table, then the Watermark wordmark]

> A Ring flood sensor, a Ring camera, and a record that starts the second the water does.
> That's Watermark.

## On-screen text, exact

- 0:15 "Controlled test. Real device."
- 0:37 "Camera: Ring Developer Playground, real Ring API. Sensor event: simulated."
- 0:52 "The first Ring frame arrived 6.7 s after the sensor event, median of 5 runs, range 6.6 to 7.1 s."
- 1:08 "Ring's timestamp, burned in by Ring."

## Screen b-roll (recorded automatically, `demo/broll/`)

| Clip | What it shows | Used at |
|---|---|---|
| `01-dashboard.webm` | Dashboard in Playground mode: the hatched notice, the sensor gauge, five incidents | 0:37 |
| `02-incident-gauge.webm` | Incident page: 6.7 s readout, the staff gauge rising, the marks below | 0:52 |
| `03-incident-frames.webm` | Glide to the six Ring frames with Ring's timestamps | 1:08 |
| `04-incident-integrity.webm` | Timeline, "what this record cannot vouch for", the claim map | 1:20 |
| `05-pack.webm` | The evidence pack, scrolled top to bottom | 1:26 |
| `06-link.webm`, `07-setup.webm`, `08-home.webm` | Account link, setup and home pages, if a beat needs cover | spare |
| `ring-frame-*.jpg` | Full-size Ring frames for stills | spare |

Re-record with `py tools/record_broll.py --incident <id>` against a server holding the
measured Playground runs.

## Hardware shots I film myself

1. **H1, June 20 stills.** Two frames from the phone videos of the flood (window well,
   panel wall). Blur the address and anything with a unit number.
2. **H2, sensor into water.** The Flood & Freeze sensor lowered into a shallow tray, at the
   water heater if possible. Steady shot, 5 to 8 seconds, label added in edit.
3. **H3, the Ring app alert.** Screen-record the phone as the flood alert arrives, with the
   phone's clock visible. Do H2 and H3 in the same take if a second person can hold the phone.
4. **H4, the Indoor Cam on the tray.** Point Flood Cam at the tray while the water goes in,
   then export that clip from the Ring app. Spare footage if Ring recorded anything.
5. **H5, the motion check.** In the Ring app, open Flood Cam's event history for the minutes
   of H2 and screen-record it. Whatever it shows is what the script says: if a motion event
   did appear, change the 0:27 line to match before recording the voice.
6. **H6, closing table shot.** Sensor, Indoor Cam and Chime side by side on a plain surface.

## Before recording the voice

- `py tools/check_claims.py` is green.
- H5 has been watched and the 0:27 line matches what it showed.
- The claim map still says TEMPLATE until the real June claim questions replace
  `server/watermark/claim_questions.json`; the script does not quote a count from it.
