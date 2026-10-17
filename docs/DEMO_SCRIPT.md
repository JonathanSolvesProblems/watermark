# Demo script (v5, as recorded)

2:56 in all: a 3.5 s title card, 2:48 of my voice, and the end card. Recorded in two takes on
16 October and cut together; I read it in my own words rather than word for word from v4.
Every number on screen is checked by `py tools/check_claims.py` against `docs/runs/`. No music.
No third-party logos; plates, house numbers and signs are blurred.

## Narration as cut

**0:00 Two floods** (Potential Impact)

> On December 5th of last year, I unfortunately had a multi-level flood in my home because there
> was a pipe sloped the wrong way on my upstairs toilet. Luckily I was home, so I was able to get
> some videos of it real quick as it was happening. But I realized now that it's really important
> to get as much pictures and videos right away, just for the insurance to be able to justify the
> amounts. And it is a condo, so it took a lot of time to get the approvals just to get the work
> started. And it took over six months with everything as a result. And when I moved back in
> finally, it was a beautiful home. I got hardwood engineered flooring. Unfortunately, one week
> later, my basement got flooded this time again, because we got so much rain and there was an
> issue with the foundations. There was cracks in the wall next to the electrical panel. So there
> was over 60 units within my condo that were all flooded.

**0:58 The idea** (Quality of the Idea)

> And this inspired an application that I built called Watermark. And it is a Ring Appstore app
> that turns a flood sensor's alert into evidence an insurer can use. And I use a real sensor, a
> real Indoor Cam. And to simulate this, I'm going to fill this bowl very slowly. And we can see
> that Ring alerts my phone right away.

**1:23 The gap** (Quality of the Idea: understanding the end user)

> But the camera's history for those minutes shows only [N] recordings. So slow water doesn't trip
> motion detection, and the Chime can't sound for a flood sensor at all.

**1:34 Watermark closes it** (Tech Implementation)

> When the sensor fires, Watermark opens a live session through the Ring Partner API, which makes
> the camera record, and keeps pulling frames with Ring's own timestamps until it's dry. Across 10
> runs on Ring's Developer Playground, the first frame landed in under seven seconds. The sensor
> there is simulated, and the pack says so.

**1:55 What you hand the insurer** (Design)

> You get one evidence pack: the timeline, the frames, device health, and what the record can't
> vouch for. Against the seven questions my adjuster actually asked, it answers the two that
> mattered, when the water came in and where it was, and partly answers two more. It never names
> a cause.

**2:17 What it's built on** (Tech Implementation)

> It's built on the Ring Partner API through a Python client I open sourced, a rover I printed
> with my 3D printer that can carry the camera to the room, with its orders sent through AWS IoT
> Core.

**2:32 Who it's for** (Potential Impact)

> A property manager or insurer with sensors in every unit gets this record for all of them,
> without anyone home. And for Ring, the flood sensor becomes a reason to add a camera. Next time
> water comes in, I won't need to be home.

## Still to record

- **The [N] line.** I said "only a certain number of recordings" as a placeholder. Re-record that
  one sentence with the real count from the Indoor Cam's event history (shot H6 below).
- **The rover line.** Keep it only if the rover passes 4 of 5 trials (`ROVER_TRIALS.md`).
  Otherwise re-record: "It's built on the Ring Partner API through a Python client I open
  sourced, with a rover dispatch over AWS IoT Core that I'm still testing."

## Shots as cut

| Time | Picture | Lower third |
|---|---|---|
| 0:00 | Opened ceiling over the dining room, 5 Dec photo | My home, December 5, 2025 |
| 0:06 | Plumber's level on the drain pipe (face cropped out) | The drain pipe, measured February 2026 |
| 0:11 | The bathroom upstairs, blurred and greyed, "getting cooked" sticker | The toilet upstairs |
| 0:14 | Water pouring through the ceiling (video) | Bucket placed right after |
| 0:17 | Dining room and blanket photos, then the rug | Bucket placed right after (first two) |
| 0:26 | Repair grid: eight dated photos popping in, March to June | The repairs, March to June 2026 |
| 0:35 | The finished basement, the new hardwood | |
| 0:40 | June 20: water spreading across the hardwood (video) | June 20, 2026 |
| 0:44 | Rain streaming over the patio roof (video) | |
| 0:47 | Where it came in at the foundation, by the pipe | |
| 0:49 | Opened wall by the electrical panel (video) | |
| 0:54 | The flooded street, plates and signs blurred | The condo's street, June 20, 2026 |
| 0:58 | Live link: incident page, home page | |
| 1:10 to 1:34 | To film: H1 kit, H3 pour, H4 alert, H6 event history, H7 Chime list | |
| 1:34 | Live link: incident frames, dashboard | Frames through the Ring Partner API; Median 6.85 s, range 6.6 to 11.2 s, 10 runs |
| 1:51 | Evidence pack, scrolled | Ring Developer Playground, simulated sensor; 2 of 7 answered, 2 partly |
| 2:17 | ring-partner-py on GitHub | github.com/JonathanSolvesProblems/ring-partner-py |
| 2:21 | To film: the rover carrying the Indoor Cam | |
| 2:32 | The flooded street again; setup page; dashboard | |
| 2:48 | End card: headshot, Watermark, jonathansolvesproblems.com, repo link | |

## Hardware shots I film myself

One controlled test with the real devices, landscape, 1080p or 4K, 30 fps:

1. **H1, the kit.** Flood & Freeze sensor and Indoor Cam beside the bowl. About 4 s.
2. **H3, the pour.** Water poured slowly into the bowl with the sensor inside. "Controlled test.
   Real device." goes on in the edit. Note the clock time when the water touches the sensor.
3. **H4, the Ring alert.** Screen-record the phone as the flood alert arrives, clock visible.
4. **H6, the ablation.** The Indoor Cam's event history for the minutes of H3, screen-recorded,
   plus a screenshot. The count fills `ring_app_motion_events` in `docs/runs/ablation-run.json`
   and the [N] line. Whatever it shows is what the voice says.
5. **H7, the Chime gap.** Chime > Audio Settings > Chime Alerts, screen-recorded scrolling the
   list: the flood sensor is not offered.
6. **The rover**, only if it passes its trials.

Crop anything in the Ring app that shows my email, my address or my location name.

## How it maps to the judging criteria

| Criterion | Where it is earned |
|---|---|
| Tech Implementation | 1:34 and 2:17: live sessions and sensor webhooks through the Ring Partner API, real Ring frames with Ring's timestamps, the open-source client, IoT Core dispatch |
| Design | 1:51: one finished pack a homeowner hands over, plus the incident page and dashboard |
| Potential Impact | 0:00: both of my floods on my own footage, more than 60 units in one building; 2:32: property managers and insurers |
| Quality of the Idea | 1:23: the gap only someone who owns the devices finds (slow water does not trip motion, the Chime cannot sound for a sensor), and the refusal to name a cause |
