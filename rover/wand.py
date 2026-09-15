"""The moisture wand: an Arduino Uno with a DHT11, an analog water sensor and an
HC-SR04, printing one CSV line per second over USB serial:

    millis,humidity_pct,temp_c,water_raw,distance_cm

The Pi reads it in a background thread and exposes the latest reading. `wet`
is what stops the rover at the water's edge, so it is computed here from the
calibrated threshold and not inferred anywhere else.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class Reading:
    ts: float
    humidity: float | None
    temperature: float | None
    water_raw: int | None
    distance_cm: float | None


def parse_line(line: str) -> Reading | None:
    parts = line.strip().split(",")
    if len(parts) != 5 or parts[0] == "millis":
        return None
    try:
        h = float(parts[1])
        t = float(parts[2])
        w = int(float(parts[3]))
        d = float(parts[4])
    except ValueError:
        return None
    return Reading(ts=time.time(), humidity=None if h < 0 else h, temperature=None if t < -40 else t,
                   water_raw=w, distance_cm=None if d < 0 else d)


class Wand:
    def __init__(self, port: str | None, baud: int = 9600, wet_threshold: int = 300):
        self.port = port
        self.baud = baud
        self.wet_threshold = wet_threshold
        self.latest: Reading | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None

    def start(self) -> None:
        if not self.port:
            return
        self._thread = threading.Thread(target=self._run, name="wand", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            import serial  # pyserial
            ser = serial.Serial(self.port, self.baud, timeout=2)
        except Exception as e:  # noqa: BLE001
            self.error = f"wand serial unavailable: {e}"
            return
        while not self._stop.is_set():
            try:
                line = ser.readline().decode("utf-8", "ignore")
            except Exception as e:  # noqa: BLE001
                self.error = f"wand read failed: {e}"
                time.sleep(1)
                continue
            r = parse_line(line)
            if r:
                self.latest = r

    def feed(self, line: str) -> None:
        """For tests and for a Pi without the Arduino attached."""
        r = parse_line(line)
        if r:
            self.latest = r

    @property
    def wet(self) -> bool:
        r = self.latest
        return bool(r and r.water_raw is not None and r.water_raw >= self.wet_threshold)

    def telemetry(self) -> dict:
        r = self.latest
        if not r:
            return {"wand": "no reading", "error": self.error}
        return {"humidity": r.humidity, "temperature": r.temperature, "water_raw": r.water_raw,
                "distance_cm": r.distance_cm, "wet": self.wet, "age_s": round(time.time() - r.ts, 1)}

    def stop(self) -> None:
        self._stop.set()
