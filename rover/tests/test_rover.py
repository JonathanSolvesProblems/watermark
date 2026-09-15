import itertools

import httpx

from rover.agent import Agent, ServerLink, load_routes
from rover.config import RoverConfig
from rover.hardware import SimHardware, SimWorld
from rover.navigate import LineFollower
from rover.wand import Wand, parse_line


def _cfg(**kw):
    c = RoverConfig(simulate=True, max_run_s=60, line_lost_timeout_s=1.5)
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def _clock():
    t = itertools.count(0, 0.03)
    return lambda: next(t)


def test_follower_stops_at_water():
    hw = SimHardware(SimWorld(water_at_m=1.0, drift_per_s=0.2))
    res = LineFollower(hw, _cfg(), sleep=lambda s: None, clock=_clock()).run()
    assert res.stop_reason == "wet"
    assert hw.world.pos_m >= 1.0
    assert hw.world.log[-1].startswith("drive")


def test_follower_reports_blocked():
    hw = SimHardware(SimWorld(water_at_m=None, obstacle_at_m=0.5))
    res = LineFollower(hw, _cfg(), sleep=lambda s: None, clock=_clock()).run()
    assert res.stop_reason == "blocked" and res.sonar_cm is not None and res.sonar_cm < 18


def test_follower_stops_at_crossbar():
    hw = SimHardware(SimWorld(water_at_m=None, crossbar_at_m=0.7, drift_per_s=0.0))
    res = LineFollower(hw, _cfg(), sleep=lambda s: None, clock=_clock()).run()
    assert res.stop_reason == "end"
    assert 0.6 < hw.world.pos_m < 0.8


def test_follower_reports_lost_when_tape_runs_out():
    hw = SimHardware(SimWorld(water_at_m=None, line_length_m=0.8, drift_per_s=0.0))
    res = LineFollower(hw, _cfg(), sleep=lambda s: None, clock=_clock()).run()
    # Past the end of the tape all sensors go dark; after the lost timeout it stops.
    assert res.stop_reason == "lost"
    assert hw.world.pos_m > 0.8


def test_follower_corrects_drift():
    hw = SimHardware(SimWorld(water_at_m=2.0, drift_per_s=0.35))
    res = LineFollower(hw, _cfg(), sleep=lambda s: None, clock=_clock()).run()
    assert res.stop_reason == "wet"
    turns = [l for l in hw.world.log if "+0.14 +0.60" in l or "+0.60 +0.14" in l]
    assert turns, "expected steering corrections while drifting"


def test_wand_parse_and_wet():
    w = Wand(None, wet_threshold=300)
    assert parse_line("millis,humidity_pct,temp_c,water_raw,distance_cm") is None
    w.feed("12345,55.0,21.5,120,88")
    assert not w.wet and w.telemetry()["humidity"] == 55.0
    w.feed("13345,62.0,21.4,510,12")
    assert w.wet and w.telemetry()["water_raw"] == 510
    assert parse_line("garbage") is None
    r = parse_line("1,-1,-99,10,-1")
    assert r.humidity is None and r.temperature is None and r.distance_cm is None


def test_agent_dispatch_reports_over_http():
    calls = []

    def handler(req: httpx.Request):
        assert req.headers["X-Rover-Token"] == "tok"
        if req.url.path == "/rover/report":
            calls.append(httpx.Response(200).json if False else __import__("json").loads(req.read()))
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    cfg = _cfg(rover_token="tok", server_url="http://srv")
    link = ServerLink(cfg, client=httpx.Client(base_url="http://srv", transport=httpx.MockTransport(handler),
                                                headers={"X-Rover-Token": "tok"}))
    hw = SimHardware(SimWorld(water_at_m=0.6))
    wand = Wand(None)
    wand.feed("1,58.0,20.9,50,60")
    agent = Agent(cfg, hw, link, commands=None, wand=wand,
                  routes={"route-water-heater": {"name": "Hall to water heater", "max_run_s": 30}}, sleep=lambda s: None)
    agent.dispatch({"cmd": "dispatch", "incident_id": "inc-1", "route_id": "route-water-heater"})
    kinds = [c["kind"] for c in calls]
    assert kinds == ["ack", "wet"], kinds
    assert calls[1]["data"]["stop_reason"] == "wet" and calls[1]["data"]["humidity"] == 58.0
    assert calls[1]["incident_id"] == "inc-1"


def test_agent_unknown_route_does_not_move():
    calls = []

    def handler(req: httpx.Request):
        calls.append(__import__("json").loads(req.read()))
        return httpx.Response(200, json={"ok": True})

    cfg = _cfg()
    link = ServerLink(cfg, client=httpx.Client(base_url="http://srv", transport=httpx.MockTransport(handler)))
    hw = SimHardware(SimWorld())
    agent = Agent(cfg, hw, link, commands=None, routes={}, sleep=lambda s: None)
    agent.dispatch({"cmd": "dispatch", "incident_id": "inc-2", "route_id": "nope"})
    assert [c["kind"] for c in calls] == ["ack", "error"]
    assert not any(l.startswith("drive +") for l in hw.world.log)


def test_routes_file_loads():
    routes = load_routes("routes.yaml")
    assert "route-water-heater" in routes and routes["route-water-heater"]["max_run_s"] == 90
