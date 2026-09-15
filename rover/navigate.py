"""Line following with three guards.

The rover follows a painter's-tape line from its dock to a sensor's room. It
stops, in this order of priority, when:

  1. the wand touches water          -> "wet"      (this IS the destination)
  2. the sonar sees something close  -> "blocked"  (report and capture from here)
  3. the line ends (all sensors off) -> "end"      (the tape ends at the room)
  4. the line is lost for too long   -> "lost"
  5. the run exceeds max_run_s       -> "timeout"

Bang-bang steering on three TCRT5000 sensors. It is not elegant and it does not
need to be: AA-powered TT motors sag over a run and a proportional controller
tuned at full charge is wrong ten minutes later, while bang-bang keeps working.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .config import RoverConfig
from .hardware import Hardware


@dataclass
class DriveResult:
    stop_reason: str            # wet | blocked | end | lost | timeout | aborted
    elapsed_s: float
    sonar_cm: float | None
    ticks: int
    notes: list[str] = field(default_factory=list)


class LineFollower:
    def __init__(self, hw: Hardware, cfg: RoverConfig, wet_fn=None, abort_fn=None, sleep=time.sleep, clock=time.monotonic):
        self.hw = hw
        self.cfg = cfg
        self.wet_fn = wet_fn or hw.wet
        self.abort_fn = abort_fn or (lambda: False)
        self.sleep = sleep
        self.clock = clock

    def run(self, max_run_s: float | None = None, tick_s: float = 0.03) -> DriveResult:
        cfg = self.cfg
        limit = max_run_s or cfg.max_run_s
        t0 = self.clock()
        last_seen = t0
        last_dir = 0          # -1 left, +1 right: which way to hunt when the line is lost
        ticks = 0
        notes: list[str] = []
        try:
            while True:
                ticks += 1
                now = self.clock()
                if self.abort_fn():
                    return self._stop("aborted", t0, ticks, notes)
                if now - t0 > limit:
                    return self._stop("timeout", t0, ticks, notes)
                if self.wet_fn():
                    return self._stop("wet", t0, ticks, notes)
                d = self.hw.sonar_cm()
                if d is not None and 0 < d < cfg.sonar_stop_cm:
                    notes.append(f"obstacle at {d:.0f} cm")
                    return self._stop("blocked", t0, ticks, notes, sonar=d)

                left, center, right = self.hw.line()
                s, ts = cfg.speed, cfg.turn_speed
                if center and not left and not right:
                    self.hw.drive(s, s)
                    last_seen = now
                elif left and not right:
                    self.hw.drive(s * 0.25, ts)          # line is to the left: turn left
                    last_dir = -1
                    last_seen = now
                elif right and not left:
                    self.hw.drive(ts, s * 0.25)          # line is to the right: turn right
                    last_dir = 1
                    last_seen = now
                elif left and center and right:
                    # A crossbar: the end-of-line marker at the room.
                    return self._stop("end", t0, ticks, notes)
                elif not (left or center or right):
                    if now - last_seen > cfg.line_lost_timeout_s:
                        return self._stop("lost", t0, ticks, notes)
                    if now - last_seen > 0.4:
                        # Hunt: rotate toward where the line was last seen.
                        if last_dir <= 0:
                            self.hw.drive(-ts * 0.6, ts * 0.6)
                        else:
                            self.hw.drive(ts * 0.6, -ts * 0.6)
                    else:
                        self.hw.drive(s * 0.6, s * 0.6)  # coast briefly; a gap in the tape
                else:
                    self.hw.drive(s, s)
                    last_seen = now
                self.sleep(tick_s)
        finally:
            self.hw.stop()

    def _stop(self, reason: str, t0: float, ticks: int, notes: list[str], sonar: float | None = None) -> DriveResult:
        self.hw.stop()
        return DriveResult(stop_reason=reason, elapsed_s=round(self.clock() - t0, 2), sonar_cm=sonar, ticks=ticks,
                           notes=notes)


def return_home(hw: Hardware, cfg: RoverConfig, seconds: float, sleep=time.sleep) -> None:
    """v0: reverse along the same line by spinning 180 degrees and following it
    back. Spin time is calibrated per chassis; `seconds` is the outbound run time
    and the return follows the line until it ends at the dock crossbar."""
    hw.drive(cfg.turn_speed, -cfg.turn_speed)
    sleep(cfg_spin_180_s(cfg))
    hw.stop()
    LineFollower(hw, cfg, wet_fn=lambda: False).run(max_run_s=min(cfg.max_run_s, seconds + 15))


def cfg_spin_180_s(cfg: RoverConfig) -> float:
    # Measured on the RenoScout 4WD base at 0.6 PWM on fresh AAs; re-measure and
    # put the number in config when the batteries or floor change.
    return getattr(cfg, "spin_180_s", 1.9)
