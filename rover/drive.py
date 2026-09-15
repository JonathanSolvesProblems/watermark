#!/usr/bin/env python3
"""Keyboard teleop, kept from the RenoScout build. Runs ON THE PI.

    python -m rover.drive          # w/a/s/d, space=stop, l=print line sensors, q=quit

Use it to lay and check a tape route: drive along the line watching `l` output
until all three sensors read the way you expect, then let `agent.py` do it.
"""
from __future__ import annotations

import sys

from .config import RoverConfig
from .hardware import make_hardware


def _getch() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main() -> None:
    cfg = RoverConfig.from_env()
    hw = make_hardware(cfg)
    s = cfg.speed
    print(__doc__)
    try:
        while True:
            c = _getch().lower()
            if c == "q":
                break
            elif c == "w":
                d = hw.sonar_cm()
                if d is not None and 0 < d < cfg.sonar_stop_cm:
                    print(f"  blocked ({d:.0f} cm), holding")
                    hw.stop()
                else:
                    hw.drive(s, s)
            elif c == "s":
                hw.drive(-s, -s)
            elif c == "a":
                hw.drive(-cfg.turn_speed, cfg.turn_speed)
            elif c == "d":
                hw.drive(cfg.turn_speed, -cfg.turn_speed)
            elif c == " ":
                hw.stop()
            elif c == "l":
                print("  line L/C/R:", hw.line(), " sonar:", hw.sonar_cm(), " wet:", hw.wet())
    except KeyboardInterrupt:
        pass
    finally:
        hw.close()
        print("\nstopped.")


if __name__ == "__main__":
    main()
