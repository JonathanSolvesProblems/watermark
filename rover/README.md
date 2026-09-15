# rover/

The part of Watermark with wheels. A Raspberry Pi 4 on the printed RenoScout 4WD
chassis carries a **Ring Indoor Cam** on the camera riser and a moisture wand on
its nose. When the server says `dispatch`, it follows a painter's-tape line to the
room the flood sensor is in and stops at the water's edge. Every judged frame
comes from the Ring cam through the Ring Partner API; the Pi never captures
evidence.

```
Ring flood sensor ──webhook──► server ──dispatch──► rover ──follows tape──► water's edge
                                                                 │
                                        server ◄──on_station/wet/blocked/telemetry──┘
                                          │
                                          └──► live session on the rover's Ring cam ──► frames ──► pack
```

## Files

| File | What |
|---|---|
| `agent.py` | The service. Polls for commands (local HTTP long-poll, or AWS IoT Core MQTT), drives, reports. |
| `navigate.py` | Bang-bang line follower with three guards: wet, blocked, end of line. |
| `hardware.py` | gpiozero on the Pi, or a scripted simulation for tests and laptops. |
| `wand.py` | Reads the Arduino's CSV (DHT11 + water sensor + HC-SR04). `wet` is the stop. |
| `drive.py` | Keyboard teleop for laying and checking a route. |
| `routes.yaml` | One entry per tape line; ids must match what the web app assigns to sensors. |
| `arduino/moisture_wand.ino` | Arduino sketch for the wand. |

## Wiring (BCM)

Same as the RenoScout drive base, plus the line sensors:

```
L298N IN1/IN2 <- GPIO17/27 (left pair)     IN3/IN4 <- GPIO22/23 (right pair)
ENA/ENB jumpers ON.  4xAA (6 V) -> +12V/GND.  Pi GND <-> L298N GND (common ground).
HC-SR04: TRIG GPIO5, ECHO GPIO6 (through a divider on ECHO).
TCRT5000 x3: OUT -> GPIO20 (left), GPIO21 (centre), GPIO26 (right); VCC 3.3 V; GND.
Arduino Uno on USB (the wand). Ring Indoor Cam on its own 5 V power bank.
```

The Pi has its own USB power bank. Never feed the Pi from the L298N's 5 V pin.

## Run

On the Pi:

```sh
pip install -e ".[pi]"
export WATERMARK_SERVER=http://<laptop-or-server>:8000 ROVER_TOKEN=<same as server>
python -m rover.agent
```

Laptop, no hardware:

```sh
ROVER_SIMULATE=1 WATERMARK_SERVER=http://localhost:8000 python -m rover.agent
```

Then `POST /api/test/trigger` on the server and watch the agent ack, "drive", hit
simulated water and report `wet`.

## Laying a route

1. Painter's tape from the dock to the sensor's room. Curves, not corners; the
   follower is bang-bang and a right angle loses the line.
2. A short strip of tape **across** the line at the room is the end marker.
3. `python -m rover.drive`, press `l` while pushing the rover along the tape: the
   centre sensor should read `True` on the tape and `False` beside it. If it is
   inverted, flip `line_active_low` in `config.py`.
4. Add the route to `routes.yaml`, then assign it to the sensor on the web app's
   Setup page.

## The Sept 26 gate

The rover is in the demo only if it reaches station on 4 of 5 dispatches. Log
each attempt in `docs/ROVER_TRIALS.md` with the stop reason and elapsed time.
