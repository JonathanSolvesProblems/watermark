# Rover wiring: Pi 4, L298N, four TT motors

The pins below are the ones `rover/config.py` already uses, so nothing in the code changes.
Work with the batteries disconnected until step 5.

## What connects to what

| From | To | Why |
|---|---|---|
| Left front + left rear motor (wired in parallel) | L298N **OUT1 / OUT2** | one channel drives the whole left side |
| Right front + right rear motor (in parallel) | L298N **OUT3 / OUT4** | right side |
| Pi **pin 11** (GPIO 17) | L298N **IN1** | left forward |
| Pi **pin 13** (GPIO 27) | L298N **IN2** | left backward |
| Pi **pin 15** (GPIO 22) | L298N **IN3** | right forward |
| Pi **pin 16** (GPIO 23) | L298N **IN4** | right backward |
| Pi **pin 6** (GND) | L298N **GND** terminal | shared ground: without it the IN signals mean nothing |
| Battery pack **+** (4xAA or 2x18650) | L298N **+12V** terminal | motor power |
| Battery pack **-** | L298N **GND** terminal (same screw as the Pi ground) | |
| Power bank | Pi USB-C | the Pi has its own supply |

Pin numbers are the physical header positions: pin 1 is the corner pin nearest the SD
card, odd pins on the inside row, even pins on the outside row.

**Leave the ENA and ENB jumpers ON.** Speed is PWM on the IN pins (gpiozero `Motor`), so the
enable pins stay high. **Leave the 5V jumper on** with a pack under 12 V, but never take the
Pi's power from the L298N's 5V screw: its regulator is not clean enough for a Pi.

Parallel motors: on each side, join the two motors' red wires together and their black
wires together, then put that pair into the OUT pair for that side. If one wheel on a side
turns the opposite way to its partner, swap that one motor's two wires.

## Steps

1. Wheels off the ground (the chassis on a box or a roll of tape).
2. Motors to OUT1-OUT4 as above. Tighten the screw terminals; TT leads are thin and slip out.
3. Four jumper wires from Pi pins 11, 13, 15, 16 to IN1-IN4, and pin 6 to the L298N GND screw.
4. Battery pack to +12V and GND (with the Pi's ground on the same GND screw).
5. Power the Pi, then connect the battery. The L298N's red LED should light.
6. On the Pi: `cd ~/watermark && python -m rover.motor_test`. It asks before each step and
   says which wheels should move.

## If something is wrong

| You see | Fix |
|---|---|
| Nothing moves, LED on | Pi GND not on the L298N GND screw, or ENA/ENB jumpers off |
| Nothing moves, LED off | battery pack flat, or + and - swapped at the terminal |
| The other side moves | swap IN1/IN2 with IN3/IN4 at the L298N |
| A side spins backwards | swap that side's two motor wires at its OUT pair |
| Motors hum but barely turn | weak batteries, or run `--speed 0.7`; TT motors stall under about 0.35 |
| Pi reboots when motors start | the Pi is sharing the motor pack: give it the power bank |

Once all six steps pass, the rover's own drive code turns the wheels the same way, and the
next step is the line sensors and the five trials in `ROVER_TRIALS.md`.
