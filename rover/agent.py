"""The rover agent. Runs on the Pi as a service.

    python -m rover.agent            # reads env: WATERMARK_SERVER, ROVER_TOKEN, ROVER_TRANSPORT
    ROVER_SIMULATE=1 python -m rover.agent   # no GPIO, scripted world (laptop)

Loop: wait for a command (long-poll the server, or an IoT Core subscription),
acknowledge, follow the route's line until a guard stops it, report the stop
reason with the wand's readings, then keep streaming telemetry until the server
sends `return_home`.

Reports always go over HTTPS to the server, whichever transport delivered the
command, so a Pi behind NAT never needs an inbound port.
"""
from __future__ import annotations

import json
import logging
import queue
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

from .config import RoverConfig
from .hardware import Hardware, make_hardware
from .navigate import LineFollower, return_home
from .wand import Wand

log = logging.getLogger("rover")


class ServerLink:
    """HTTPS to the Watermark server: reports, and (local transport) commands."""

    def __init__(self, cfg: RoverConfig, client: httpx.Client | None = None):
        self.cfg = cfg
        self.http = client or httpx.Client(base_url=cfg.server_url, timeout=70.0,
                                           headers={"X-Rover-Token": cfg.rover_token})

    def next_command(self, wait_s: float = 25.0) -> dict[str, Any] | None:
        r = self.http.get("/rover/commands", params={"rover_id": self.cfg.rover_id, "wait": wait_s})
        r.raise_for_status()
        return r.json().get("command")

    def report(self, incident_id: str, kind: str, message: str = "", data: dict[str, Any] | None = None) -> None:
        body = {"incident_id": incident_id, "kind": kind, "message": message,
                "data": {"rover_id": self.cfg.rover_id, "ts_ms": int(time.time() * 1000), **(data or {})}}
        try:
            self.http.post("/rover/report", json=body).raise_for_status()
        except Exception as e:  # noqa: BLE001
            log.warning("report %s failed: %s", kind, e)


class IoTCommands:
    """Subscribe to `<prefix>/<rover_id>/commands` on AWS IoT Core with the Thing's
    certificate. Commands land in a queue the agent drains."""

    def __init__(self, cfg: RoverConfig):
        from awscrt import mqtt
        from awsiot import mqtt_connection_builder

        self.q: queue.Queue[dict[str, Any]] = queue.Queue()
        self.conn = mqtt_connection_builder.mtls_from_path(
            endpoint=cfg.iot_endpoint, cert_filepath=cfg.iot_cert, pri_key_filepath=cfg.iot_key,
            ca_filepath=cfg.iot_root_ca, client_id=cfg.rover_id, clean_session=False, keep_alive_secs=30)
        self.conn.connect().result()
        topic = f"{cfg.iot_topic_prefix.rstrip('/')}/{cfg.rover_id}/commands"
        self.conn.subscribe(topic=topic, qos=mqtt.QoS.AT_LEAST_ONCE, callback=self._on_message)[0].result()
        log.info("subscribed to %s", topic)

    def _on_message(self, topic, payload, **kw):
        try:
            self.q.put(json.loads(payload))
        except Exception as e:  # noqa: BLE001
            log.warning("bad IoT payload: %s", e)

    def next_command(self, wait_s: float = 25.0) -> dict[str, Any] | None:
        try:
            return self.q.get(timeout=wait_s)
        except queue.Empty:
            return None


def load_routes(path: str | Path) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).with_name(str(path))
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("routes", {})


class Agent:
    def __init__(self, cfg: RoverConfig, hw: Hardware, link: ServerLink, commands, wand: Wand | None = None,
                 routes: dict[str, dict[str, Any]] | None = None, sleep=time.sleep):
        self.cfg = cfg
        self.hw = hw
        self.link = link
        self.commands = commands
        self.wand = wand or Wand(None)
        self.routes = routes if routes is not None else load_routes(cfg.routes_file)
        self.sleep = sleep
        self._stop = threading.Event()
        self.current_incident: str | None = None
        self.on_station_since: float | None = None
        self.outbound_s: float = 0.0

    def stop(self) -> None:
        self._stop.set()

    def wet(self) -> bool:
        return self.wand.wet or self.hw.wet()

    def handle(self, cmd: dict[str, Any]) -> None:
        kind = cmd.get("cmd")
        if kind == "dispatch":
            self.dispatch(cmd)
        elif kind == "return_home":
            self.go_home(cmd)
        else:
            log.warning("unknown command %s", kind)

    def dispatch(self, cmd: dict[str, Any]) -> None:
        incident_id = cmd.get("incident_id") or ""
        route_id = cmd.get("route_id")
        route = self.routes.get(route_id or "", {})
        self.current_incident = incident_id
        self.link.report(incident_id, "ack", f"route {route_id or 'none'}: {route.get('name', 'unknown route')}",
                         {"route_known": bool(route)})
        if not route:
            self.link.report(incident_id, "error", f"route {route_id} not in routes.yaml; not moving")
            return
        follower = LineFollower(self.hw, self.cfg, wet_fn=self.wet, abort_fn=self._stop.is_set, sleep=self.sleep)
        res = follower.run(max_run_s=float(route.get("max_run_s", self.cfg.max_run_s)))
        self.outbound_s = res.elapsed_s
        data = {"stop_reason": res.stop_reason, "elapsed_s": res.elapsed_s, "sonar_cm": res.sonar_cm,
                "ticks": res.ticks, "notes": res.notes, **self.wand.telemetry()}
        if res.stop_reason == "wet":
            self.link.report(incident_id, "wet", f"wand touched water after {res.elapsed_s} s", data)
        elif res.stop_reason == "blocked":
            self.link.report(incident_id, "blocked", f"path blocked at {res.sonar_cm:.0f} cm after {res.elapsed_s} s"
                             if res.sonar_cm is not None else "path blocked", data)
        elif res.stop_reason == "end":
            self.link.report(incident_id, "on_station", f"reached end of route after {res.elapsed_s} s", data)
        else:
            self.link.report(incident_id, "error", f"stopped: {res.stop_reason} after {res.elapsed_s} s", data)
            if res.stop_reason in ("lost", "timeout"):
                # Still worth a look from wherever it is; the pack will say the rover never confirmed the room.
                pass
        self.on_station_since = time.time()

    def go_home(self, cmd: dict[str, Any]) -> None:
        incident_id = cmd.get("incident_id") or self.current_incident or ""
        try:
            return_home(self.hw, self.cfg, self.outbound_s, sleep=self.sleep)
            self.link.report(incident_id, "returned", "back at dock")
        except Exception as e:  # noqa: BLE001
            self.link.report(incident_id, "error", f"return failed: {e}")
        self.current_incident = None
        self.on_station_since = None

    def run_forever(self) -> None:
        log.info("rover %s ready (transport=%s, simulate=%s)", self.cfg.rover_id, self.cfg.transport, self.cfg.simulate)
        last_tel = 0.0
        while not self._stop.is_set():
            try:
                cmd = self.commands.next_command(wait_s=self.cfg.telemetry_every_s if self.current_incident else 25.0)
            except Exception as e:  # noqa: BLE001
                log.warning("command poll failed: %s", e)
                self.sleep(3)
                continue
            if cmd:
                try:
                    self.handle(cmd)
                except Exception as e:  # noqa: BLE001
                    log.exception("command failed: %s", e)
                    if self.current_incident:
                        self.link.report(self.current_incident, "error", f"{type(e).__name__}: {e}")
            if self.current_incident and time.time() - last_tel >= self.cfg.telemetry_every_s:
                self.link.report(self.current_incident, "telemetry", "", self.wand.telemetry())
                last_tel = time.time()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = RoverConfig.from_env()
    hw = make_hardware(cfg)
    link = ServerLink(cfg)
    commands = IoTCommands(cfg) if cfg.transport == "iot" else link
    wand = Wand(cfg.wand_port if not cfg.simulate else None, cfg.wand_baud, cfg.wet_threshold)
    wand.start()
    agent = Agent(cfg, hw, link, commands, wand)

    def _sig(*_):
        agent.stop()
        hw.stop()

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    try:
        agent.run_forever()
    finally:
        wand.stop()
        hw.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
