"""First power-on check for the drive wiring. Runs ON THE PI, wheels off the ground.

    python -m rover.motor_test           # each side forward then back, one second each
    python -m rover.motor_test --speed 0.4

Uses the same pins as the rover (config.py), so if this passes the rover's own
drive code will turn the wheels the same way. It says which wheels should move at
each step: if the wrong side moves, swap the IN wires; if a side spins backwards,
swap that side's two motor wires at OUT1/OUT2 or OUT3/OUT4.
"""
from __future__ import annotations

import argparse
from time import sleep

from .config import RoverConfig

STEPS = [
    ("LEFT wheels FORWARD", 1, 0),
    ("LEFT wheels BACKWARD", -1, 0),
    ("RIGHT wheels FORWARD", 0, 1),
    ("RIGHT wheels BACKWARD", 0, -1),
    ("BOTH FORWARD (should roll straight ahead)", 1, 1),
    ("SPIN: left forward, right back (turns right)", 1, -1),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=0.5)
    ap.add_argument("--seconds", type=float, default=1.0)
    a = ap.parse_args()

    from gpiozero import Motor  # imported here so --help works off the Pi

    p = RoverConfig().pins
    left = Motor(forward=p.left_fwd, backward=p.left_back)
    right = Motor(forward=p.right_fwd, backward=p.right_back)

    def set_(m: Motor, v: float) -> None:
        if v > 0:
            m.forward(v)
        elif v < 0:
            m.backward(-v)
        else:
            m.stop()

    print(f"pins (BCM): left fwd {p.left_fwd} back {p.left_back}, right fwd {p.right_fwd} back {p.right_back}")
    print("Wheels OFF the ground. Ctrl+C stops everything.\n")
    try:
        for label, l, r in STEPS:
            input(f"Press Enter for: {label} ")
            set_(left, l * a.speed)
            set_(right, r * a.speed)
            sleep(a.seconds)
            left.stop()
            right.stop()
    except KeyboardInterrupt:
        pass
    finally:
        left.stop()
        right.stop()
        print("\nstopped")


if __name__ == "__main__":
    main()
