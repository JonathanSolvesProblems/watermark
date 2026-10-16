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
[Screen: 02-incident-gauge.webm. On screen: "The first Ring frame arrived 6.85 s after the
sensor event, median of 10 runs, range 6.6 to 11.2 s."]

> The sensor fires, Watermark opens a live session, and the first Ring frame is in hand in
> about seven seconds. Ten runs on two days, median six point eight five. The blue bar is
> how long the water stood; each notch is a frame.

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
- 0:52 "The first Ring frame arrived 6.85 s after the sensor event, median of 10 runs, range 6.6 to 11.2 s."
- 1:08 "Ring's timestamp, burned in by Ring."

## Screen b-roll (recorded automatically, `demo/broll/`)

| Clip | What it shows | Used at |
|---|---|---|
| `01-dashboard.webm` | Dashboard in Playground mode: the hatched notice, the sensor gauge, five incidents | 0:37 |
| `02-incident-gauge.webm` | Incident page: 6.85 s readout, the staff gauge rising, the marks below | 0:52 |
| `03-incident-frames.webm` | Glide to the six Ring frames with Ring's timestamps | 1:08 |
| `04-incident-integrity.webm` | Timeline, "what this record cannot vouch for", the claim map | 1:20 |
| `05-pack.webm` | The evidence pack, scrolled top to bottom | 1:26 |
| `06-link.webm`, `07-setup.webm`, `08-home.webm` | Account link, setup and home pages, if a beat needs cover | spare |
| `ring-frame-*.jpg` | Full-size Ring frames for stills | spare |

Re-record with `py tools/record_broll.py --incident <id>` against a server holding the
measured Playground runs.

## Hardware shots I film myself

Already shot (in `demo/broll/flood/`, picks in `FOOTAGE.md`, not committed): the December
ceiling, the June window well, me pumping by the electrical panel where it came up from the
foundation, the wet floor, the flooded street. Blur house numbers and plates.

New, one controlled test with the real devices, landscape, 1080p or 4K, 30 fps:

1. **H1, the kit.** Flood & Freeze sensor, Indoor Cam and Chime side by side on a plain
   surface. 5 s, slow push in.
2. **H2, the setup in place.** The Indoor Cam on a shelf or the floor, aimed at a shallow tray
   on the basement floor, ideally near the window or the water heater. 5 s.
3. **H3, water reaches the sensor.** The sensor in the empty tray, then water poured in
   slowly, a cup at a time, so the level rises over about 2 minutes. That slow rise is the
   point: it is how a basement floods. Film it steady, 20 to 30 s of usable footage, and note
   the clock time when the water first touches the sensor. "Controlled test. Real device."
   goes on in the edit.
4. **H4, the Ring alert.** Screen-record the phone as the flood alert arrives, clock visible.
   Same take as H3 if someone can hold the phone, otherwise right after with the clock in shot.
5. **H5, what the camera saw.** In the Ring app, open the Indoor Cam's live view while the tray
   is wet and screen-record 5 s: proof the camera could see the water.
6. **H6, the ablation.** In the Ring app, open the Indoor Cam's event history for the minutes
   of H3 and screen-record it, plus a screenshot. Count the motion recordings in that window.
   That count fills `ring_app_motion_events` in `docs/runs/ablation-run.json` and the
   "[N] motion recordings" line. Whatever it shows is what the script says.
7. **Optional, the Chime gap.** In the Ring app, the Chime (Hallway) > Audio Settings > Chime
   Alerts, screen-recorded: only Flood Cam motion is offered; the flood sensor is not on the
   list. Ring cannot make the Chime sound for water; Watermark does it through the API.
8. **Optional, me on camera.** Standing by the basement window, one line: "This is where the
   water came in on June 20th." Ten seconds of a real person in the real room.

Crop anything in the Ring app that shows my email, my address or my location name.

## Before recording the voice

- `py tools/check_claims.py` is green, with the H6 count committed.
- H6 has been watched and the ablation line matches what it showed.
