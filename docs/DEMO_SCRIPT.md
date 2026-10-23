# Demo script (v6, final cut)

2:46 in all: a 3.5 s title card, 2:38 of my voice, and the end card. Recorded in two takes on
16 October plus the count line on 22 October, after the controlled test, and cut together; I read
it in my own words rather than word for word from v4.
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

> But the camera's history for those minutes shows no recordings at all. So slow water doesn't trip
> motion detection, and the Chime can't sound for a flood sensor at all.

**1:34 Watermark closes it** (Tech Implementation)

> When the sensor fires, Watermark opens a live session through the Ring Partner API, which makes
> the camera record, and keeps pulling frames with Ring's own timestamps until it's dry. Across 10
> runs on Ring's Developer Playground, the first frame landed in under seven seconds. The sensor
> there is simulated, and the pack says so.

**1:45 What you hand the insurer** (Design)

> You get one evidence pack: the timeline, the frames, device health, and what the record can't
> vouch for. Against the seven questions my adjuster actually asked, it answers the two that
> mattered, when the water came in and where it was, and partly answers two more. It never names
> a cause.

**2:07 What it's built on** (Tech Implementation)

> It's built on the Ring Partner API through a Python client I open sourced.

**2:22 Who it's for** (Potential Impact)

> A property manager or insurer with sensors in every unit gets this record for all of them,
> without anyone home. And for Ring, the flood sensor becomes a reason to add a camera. Next time
> water comes in, I won't need to be home.

## Lines changed after the first take

- **The count line** was recorded on 22 October, after the controlled test, with the real result:
  the Indoor Cam's event history showed no recordings while the sensor sat in water
  (`docs/runs/ablation-run.json`). It replaces the placeholder "only a certain number of recordings".
- **The rover line is cut** from the take: the rover has not driven on the floor, so the video
  does not mention it. The rover is the next step, named in the written fields only.

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
| 1:10 | My Flood & Freeze sensor on the floor, then my Indoor Cam (Canon, Oct 15) | Ring Flood & Freeze Sensor; Ring Indoor Cam |
| 1:14 | The pour: water into the bowl with the sensor in it, the Indoor Cam behind (Canon, Oct 22) | Controlled test. Real device. |
| 1:19 | Phone board, 8:35 PM: the Ring alert sliding in, the bowl beside it | |
| 1:23 | Phone board, 8:38 PM: the camera's event history, nothing since 8:27 | |
| 1:27 | Water reaching the sensor, from above (Canon) | Controlled test. Real device. |
| 1:30 | Phone board, 8:40 PM: the Chime's alert list, only the camera on it; the Chime on my wall beside it | |
| 1:34 | Live link: incident frames, dashboard | Frames through the Ring Partner API; Median 6.85 s, range 6.6 to 11.2 s, 10 runs |
| 1:41 | Evidence pack, scrolled | Ring Developer Playground, simulated sensor; 2 of 7 answered, 2 partly |
| 2:07 | ringwire on GitHub | github.com/JonathanSolvesProblems/ringwire |
| 2:22 | The flooded street again; dashboard; the evidence pack | |
| 2:38 | End card: headshot, Watermark, jonathansolvesproblems.com, repo link | |

## Hardware shots (filmed 22 October, devices on 15 October)

One controlled test with the real devices, Canon 1080p, plus the phone's screen recorded over USB:

1. **H1, the kit.** The sensor and the Indoor Cam, each filmed on its own on 15 October.
2. **H3, the pour.** Water poured slowly into the bowl with the sensor inside. "Controlled test.
   Real device." goes on in the edit. Note the clock time when the water touches the sensor.
3. **H4, the Ring alert.** Screen-record the phone as the flood alert arrives, clock visible.
4. **H6, the ablation.** The Indoor Cam's event history for the minutes of H3, screen-recorded,
   plus a screenshot. The count fills `ring_app_motion_events` in `docs/runs/ablation-run.json`
   and the count line. It showed 0 on 22 October: the alert reached the phone at 20:35:10 and the
   camera recorded nothing from 20:35 to 20:38.
5. **H7, the Chime gap.** Chime > Audio Settings > Chime Alerts, screen-recorded scrolling the
   list: the flood sensor is not offered.

Crop anything in the Ring app that shows my email, my address or my location name.

## How it maps to the judging criteria

| Criterion | Where it is earned |
|---|---|
| Tech Implementation | 1:34 and 2:07: live sessions and sensor webhooks through the Ring Partner API, real Ring frames with Ring's timestamps, the open-source client, IoT Core dispatch |
| Design | 1:45: one finished pack a homeowner hands over, plus the incident page and dashboard |
| Potential Impact | 0:00: both of my floods on my own footage, more than 60 units in one building; 2:22: property managers and insurers |
| Quality of the Idea | 1:23: the gap only someone who owns the devices finds (slow water does not trip motion, the Chime cannot sound for a sensor), and the refusal to name a cause |
