# Demo script (v2, written before the first real run)

Target 85 seconds. Numbers in square brackets are placeholders; `tools/check_claims.py`
fails the build if a real number appears here without a run file behind it, and fails
again if a placeholder is still here once the run file exists. One unbroken take for the
rover's run, stopwatch visible.

```
[0:00] On June 20th the city sewer backed up into fifty-two units of my condo,
       mine included. The mitigation company's report said heavy rain, and
       floated my backyard shed as the cause. The only reason that didn't stick
       was two phone videos I took while it was happening, because I happened
       to be home.
       (stills from the two entry-point videos, blurred where needed)

[0:15] Next time I won't be. This is Watermark.

[0:19] (Flood & Freeze sensor lowered into a tray at the water heater.
       On-screen: "Controlled test. Real device.")
       Water touches the sensor. The chime plays. My phone says which room.

[0:27] Ring's sensor knows where the water is. The camera is in the other
       room. So the camera goes to the water.
       (One take: the rover wakes, follows the line down the hall, Ring Indoor
       Cam on the riser, stops at the doorway when the wand touches wet floor.
       Stopwatch in the corner.)

[0:45] (Live view from the rover's Ring cam: the puddle, timestamped.)
       Sensor at zero. Rover on station in [N] s. First frame in [N] s.
       Caption: "Water pooling along the baseboard, roughly one to two
       centimetres."

[0:55] Every five minutes, another frame. Humidity climbing. If the camera
       drops offline, the timeline says so instead of pretending.
       (Gap shown: "No visual evidence 02:31 to 02:40. Camera offline.")

[1:05] When it's over, one PDF: sensor log, route, frames with times, drying
       curve, and an integrity section listing everything it could not verify.
       Against the questions on my real claim file, it answers [N] of [M]
       questions. The cause is still the adjuster's job. The timeline is mine.

[1:18] Same test with the sensor scope off: nothing moves, and it captured
       [N] frames. That is what the sensor is worth.

[1:23] Water is now the leading cause of home insurance claims in Canada.
       This is a forty-dollar sensor, a camera, and a printed rover.
```

## Shot list

1. Two stills from the June 20 entry-point videos (window well, panel wall). Blur anything with an address.
2. Sensor into the tray. Real Flood & Freeze sensor, real water, the on-screen label.
3. Chime close-up as it plays. Phone notification in frame.
4. **The rover run, one take.** Wide shot down the hall, stopwatch overlay from the sensor event.
5. Screen capture: the incident page filling in (frames, timeline, stats).
6. Screen capture: the integrity section with an offline gap (unplug the camera for 30 seconds during a rehearsal run to get a real one).
7. Screen capture: the claim map.
8. Screen capture: the ablation incident (scope off) with zero frames.
9. Closing card: the three objects on a table.

## What must be true before recording

- The numbers exist as numbers (`docs/runs/demo-run.json` and `docs/runs/ablation-run.json` committed, `py tools/check_claims.py` green).
- The rover passed the Sept 26 gate (`docs/ROVER_TRIALS.md`).
- The claim questions in `server/watermark/claim_questions.json` are the real ones from the June file, not the template.
