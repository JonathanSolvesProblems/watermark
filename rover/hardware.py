"""Hardware abstraction: motors, sonar, line sensors, wet pin.

Real implementations use gpiozero on the Pi. `SimHardware` runs anywhere and
plays back a scripted world so `agent.py` and `navigate.py` can be tested on a
laptop. Nothing above this module imports gpiozero.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .config import RoverConfig


class Hardware:
    def drive(self, left: float, right: float) -> None:
        """left/right in -1..1. Positive is forward."""
        raise NotImplementedError

    def stop(self) -> None:
        self.drive(0.0, 0.0)

    def line(self) -> tuple[bool, bool, bool]:
        """(left, center, right): True when that sensor sees the line."""
        raise NotImplementedError

    def sonar_cm(self) -> float | None:
        return None

    def wet(self) -> bool:
        return False

    def close(self) -> None:
        pass


class PiHardware(Hardware):
    def __init__(self, cfg: RoverConfig):
        from gpiozero import DigitalInputDevice, DistanceSensor, Motor

        p = cfg.pins
        self.cfg = cfg
        self.left = Motor(forward=p.left_fwd, backward=p.left_back)
        self.right = Motor(forward=p.right_fwd, backward=p.right_back)
        self.sonar = DistanceSensor(echo=p.sonar_echo, trigger=p.sonar_trig, max_distance=2.0)
        self._line = [DigitalInputDevice(pin, pull_up=True) for pin in (p.line_left, p.line_center, p.line_right)]
        self._wet = DigitalInputDevice(p.wet_pin, pull_up=False) if p.wet_pin is not None else None

    def drive(self, left: float, right: float) -> None:
        for m, v in ((self.left, left), (self.right, right)):
            v = max(-1.0, min(1.0, v))
            if v > 0.02:
                m.forward(v)
            elif v < -0.02:
                m.backward(-v)
            else:
                m.stop()

    def line(self) -> tuple[bool, bool, bool]:
        vals = [bool(s.value) for s in self._line]
        if self.cfg.line_active_low:
            vals = [not v for v in vals]
        return vals[0], vals[1], vals[2]

    def sonar_cm(self) -> float | None:
        try:
            return self.sonar.distance * 100.0
        except Exception:  # noqa: BLE001
            return None

    def wet(self) -> bool:
        return bool(self._wet.value) if self._wet is not None else False

    def close(self) -> None:
        self.stop()
        for d in (self.left, self.right, self.sonar, *self._line):
            try:
                d.close()
            except Exception:  # noqa: BLE001
                pass


@dataclass
class SimWorld:
    """A one-dimensional corridor: the line runs from 0 to `line_length_m`, water
    starts at `water_at_m`, an obstacle may sit at `obstacle_at_m`. Drift pushes
    the rover off-centre so the follower has to correct."""

    line_length_m: float = 4.0
    water_at_m: float | None = 3.2
    obstacle_at_m: float | None = None
    crossbar_at_m: float | None = None   # a strip across the line: all three sensors read it
    speed_m_per_s: float = 0.25
    drift_per_s: float = 0.15       # lateral drift when driving straight, in "sensor widths"
    pos_m: float = 0.0
    lateral: float = 0.0            # -1 left of line .. 0 centred .. +1 right of line
    t: float = 0.0
    log: list[str] = field(default_factory=list)


class SimHardware(Hardware):
    def __init__(self, world: SimWorld | None = None, realtime: bool = False):
        self.world = world or SimWorld()
        self.realtime = realtime
        self._left = self._right = 0.0
        self._last = time.monotonic()

    def _step(self) -> None:
        now = time.monotonic()
        dt = (now - self._last) if self.realtime else 0.05
        self._last = now
        w = self.world
        fwd = (self._left + self._right) / 2.0
        turn = (self._right - self._left)      # positive = turning left
        w.pos_m += fwd * w.speed_m_per_s * dt
        w.lateral += (-turn * 2.0 + (w.drift_per_s if fwd > 0 else 0.0)) * dt
        w.lateral = max(-2.0, min(2.0, w.lateral))
        w.t += dt

    def drive(self, left: float, right: float) -> None:
        self._step()
        self._left, self._right = left, right
        self.world.log.append(f"drive {left:+.2f} {right:+.2f} pos={self.world.pos_m:.2f} lat={self.world.lateral:+.2f}")
        if self.realtime:
            time.sleep(0.02)

    def line(self) -> tuple[bool, bool, bool]:
        """Sensors sit at -0.6, 0 and +0.6 sensor-widths from centre. The line is at
        `-lateral` relative to the rover, and a sensor sees it within 0.35 widths."""
        self._step()
        w = self.world
        if w.pos_m > w.line_length_m or w.pos_m < -0.1:
            return False, False, False
        if w.crossbar_at_m is not None and abs(w.pos_m - w.crossbar_at_m) < 0.06:
            return True, True, True
        lat = w.lateral

        def sees(p: float) -> bool:
            return abs(p + lat) < 0.35

        return sees(-0.6), sees(0.0), sees(0.6)

    def sonar_cm(self) -> float | None:
        w = self.world
        if w.obstacle_at_m is None:
            return 150.0
        return max(0.0, (w.obstacle_at_m - w.pos_m) * 100.0)

    def wet(self) -> bool:
        w = self.world
        return w.water_at_m is not None and w.pos_m >= w.water_at_m


def make_hardware(cfg: RoverConfig) -> Hardware:
    if cfg.simulate:
        return SimHardware()
    return PiHardware(cfg)
