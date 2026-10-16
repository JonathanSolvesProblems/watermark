# Demo script (v4)

About 2:35, spoken at an easy pace (about 350 words). Judges are not required to watch past
3:00, so the strongest material is first: my two real floods, then the real Ring devices, then the
gap Ring leaves, then Watermark closing it. Every number on screen is checked by
`py tools/check_claims.py` against `docs/runs/`. No music, or royalty-free only. No third-party
logos: skip the fill-valve and battery photos (branded packaging), blur plates and house numbers.

## Script

**0:00 Two floods** (Potential Impact)
[December clip: the opened ceiling above the dining area, blanket on the floor. Lower third:
"5 December 2025". Then the June clip: water across the hardwood under the basement window.
Lower third: "20 June 2026, 4:35 PM".]

> December 5th. Water's coming through my ceiling from the bathroom above. The repairs took
> months. June 20th, one week after they finished, 4:35 in the afternoon. Now it's coming in
> under my basement window and through the foundation, right across the new floor.

**0:16 Why it mattered**
[Me pumping by the electrical panel, then the wet floor.]

> The sewer backed up into fifty-two units that day, and the mitigation report blamed the rain.
> My insurer needed to know: sewer, or clean rainwater? That decided my coverage. Both times,
> my only proof was my phone, because I happened to be home.

**0:32 The idea** (Quality of the Idea)
[H1 the kit, H2 the camera aimed at the tray.]

> So I built Watermark, a Ring Appstore app that turns a flood sensor's alert into evidence
> an insurer can use.

**0:41 The real devices**
[H3 the slow pour, label "Controlled test. Real device." Then H4, the Ring alert on my phone.]

> Real sensor, real Indoor Cam. I fill the tray slowly, the way a basement floods. Ring
> alerts my phone right away.

**0:51 The gap** (Quality of the Idea: understanding the end user)
[H6 the Indoor Cam's event history for those minutes. Then H7, the Chime's alert list.]

> But the camera's history for those minutes shows [N] recordings. Slow water doesn't trip
> motion detection. And the Chime can't sound for a flood sensor at all.

(Say the real count from H6, whatever it is, and adjust the next sentence to match.)

**1:03 Watermark closes it** (Tech Implementation)
[Screen: dashboard, then an incident page filling with Ring frames, Ring's timestamp in the
corner. On-screen text below.]

> When the sensor fires, Watermark opens a live session through the Ring Partner API, which
> makes the camera record, and keeps pulling frames with Ring's own timestamp until it's dry.
> Across ten runs on Ring's Developer Playground, the first frame landed in under seven
> seconds. The sensor there is simulated, and the pack says so.

**1:28 What you hand the insurer** (Design)
[The evidence pack: the plaque header with the red line, the timeline, the frames, the section
on what the record cannot vouch for, then the claim questions. On-screen text below.]

> You get one evidence pack: the timeline, the frames, device health, and what the record
> can't vouch for. Against the seven questions my adjuster actually asked, it answers the two
> that mattered, when the water came and where it was, and partly answers two more. It never
> names a cause.

**1:50 What it's built on** (Tech Implementation)
[Architecture card: sensor webhook, live session, chime playback, account linking, AWS IoT
Core, S3. Then the rover clip if it passed its trials, otherwise the IoT dispatch log.]

> It's built on the Ring Partner API, through a Python client I open-sourced. A rover I
> printed can carry the camera to the room, with its orders sent through AWS IoT Core.

**2:05 Who it's for** (Potential Impact)
[Wide shot of the street under water, plates blurred.]

> Fifty-two units flooded in my building that day. A property manager or insurer with
> sensors in every unit gets this record for all of them, without anyone home. And for Ring,
> the flood sensor becomes a reason to add a camera.

**2:24 Close**
[Final shot: the evidence pack, the plaque header and its red line, slow push in. Wordmark.]

> Next time water comes in, I won't need to be home.

## On-screen text, exact

- 0:00 lower thirds: "5 December 2025", then "20 June 2026, 4:35 PM"
- 0:41: "Controlled test. Real device."
- 0:51: "Ring app event history, Indoor Cam, during the fill: [N] motion recordings"
- 1:03: "The first Ring frame arrived 6.85 s after the sensor event, median of 10 runs, range 6.6 to 11.2 s. Ring Developer Playground; sensor simulated."
- 1:28: "The pack answers 2 of 7 questions my adjuster asked; it partly answers 2 more."
- 1:50: "Rover dispatch over AWS IoT Core: on station 7.7 seconds after the sensor (simulated drive)."
- 2:24: "Watermark. github.com/JonathanSolvesProblems/watermark"

## How the script maps to the judging criteria

| Criterion | Where it is earned |
|---|---|
| Tech Implementation | 1:03 and 1:50: live sessions, sensor webhooks, chime playback and account linking from the Ring Partner API; the open-source client; IoT Core dispatch; real Ring frames with Ring's timestamps |
| Design | 1:28: one finished artifact a homeowner hands over, plus the dashboard and incident page at 1:03 |
| Potential Impact | 0:00 and 2:05: both of my floods on my own footage, 52 units in one building, property managers and insurers as the next audience |
| Quality of the Idea | 0:51: the gap only someone who owns the devices finds (slow water does not trip motion, the Chime cannot sound for a sensor), and the refusal to name a cause |

## Screen b-roll (record with `tools/record_broll.py` against the live link)

| Clip | What | Used at |
|---|---|---|
| `01-dashboard` | Dashboard with the recorded runs, then a click into an incident | 1:03 |
| `02-incident` | Incident page: the Ring frame, the sentence with the time to first frame, the gauge | 1:03 |
| `03-pack` | The evidence pack, slow scroll from the plaque header to the claim questions | 1:28, 2:24 |
| `04-iot` | The IoT dispatch record (`docs/runs/iot-dispatch.json`) or the rover clip | 1:50 |

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
