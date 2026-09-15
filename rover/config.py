"""Rover configuration. Everything a person might touch is here; the code reads it.

Copied from the RenoScout build (Pi 4 + L298N + 4 TT motors, two per side in
parallel) and extended with the line sensor and the wand. BCM pin numbers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Pins:
    # L298N direction pins. ENA/ENB jumpers stay ON; speed is PWM on the IN pins.
    left_fwd: int = 17
    left_back: int = 27
    right_fwd: int = 22
    right_back: int = 23
    # HC-SR04 front bumper (optional)
    sonar_trig: int = 5
    sonar_echo: int = 6
    # Line sensors (TCRT5000 digital out, active LOW on most modules over dark tape).
    # One sensor works as a bang-bang follower; three is much steadier.
    line_left: int = 20
    line_center: int = 21
    line_right: int = 26
    # Water sensor on the wand: either via the Arduino serial CSV (default) or a
    # digital "wet" pin if the module has one wired straight to the Pi.
    wet_pin: int | None = None


@dataclass
class RoverConfig:
    rover_id: str = "rover-1"
    server_url: str = "http://192.168.0.92:8000"
    rover_token: str = "dev-rover-token"
    transport: str = "local"                # local (long-poll HTTP) | iot (MQTT via AWS IoT Core)
    iot_endpoint: str | None = None
    iot_cert: str | None = None             # paths for the Thing's X.509 cert, key, root CA
    iot_key: str | None = None
    iot_root_ca: str | None = None
    iot_topic_prefix: str = "watermark/rover"

    speed: float = 0.55                     # 0..1 PWM. TT motors on 4xAA sag; keep some headroom.
    turn_speed: float = 0.6
    line_active_low: bool = True            # TCRT5000 boards pull the output LOW over dark tape
    line_lost_timeout_s: float = 2.5        # off the line this long = stop and report blocked
    sonar_stop_cm: float = 18.0
    max_run_s: float = 120.0                # hard cap on any dispatch drive
    wet_threshold: int = 300                # Arduino analog water sensor: above this is wet (calibrate)
    wand_port: str | None = "/dev/ttyUSB0"  # Arduino running arduino/moisture_wand.ino; None disables
    wand_baud: int = 9600
    telemetry_every_s: float = 5.0
    routes_file: str = "routes.yaml"
    pins: Pins = field(default_factory=Pins)
    simulate: bool = False                  # no GPIO: prints what it would do (tests, laptop)

    @classmethod
    def from_env(cls) -> "RoverConfig":
        c = cls()
        c.rover_id = os.environ.get("ROVER_ID", c.rover_id)
        c.server_url = os.environ.get("WATERMARK_SERVER", c.server_url).rstrip("/")
        c.rover_token = os.environ.get("ROVER_TOKEN", c.rover_token)
        c.transport = os.environ.get("ROVER_TRANSPORT", c.transport)
        c.iot_endpoint = os.environ.get("IOT_ENDPOINT")
        c.iot_cert = os.environ.get("IOT_CERT")
        c.iot_key = os.environ.get("IOT_KEY")
        c.iot_root_ca = os.environ.get("IOT_ROOT_CA")
        c.wand_port = os.environ.get("WAND_PORT", c.wand_port) or None
        c.routes_file = os.environ.get("ROUTES_FILE", c.routes_file)
        c.simulate = os.environ.get("ROVER_SIMULATE", "0") == "1"
        if os.environ.get("ROVER_SPEED"):
            c.speed = float(os.environ["ROVER_SPEED"])
        return c
