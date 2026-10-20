"""Playground mode: the simulated sensor and its labelling, without touching the network."""
import pytest
from ringwire import Unauthorized

from watermark.config import Settings
from watermark.integrity import compute
from watermark.ring import PlaygroundRing


def _pg(tmp_path, token: str | None):
    PlaygroundRing._inst = None
    f = tmp_path / "token.txt"
    if token is not None:
        f.write_text(token)
    return PlaygroundRing(Settings(mode="playground", data_dir=tmp_path, playground_token_file=str(f)))


def test_simulated_sensor_reports_flood_state(tmp_path):
    pg = _pg(tmp_path, "t")
    assert pg.status(PlaygroundRing.SENSOR).flood_faulted is False
    pg.set_faulted(PlaygroundRing.SENSOR, True)
    assert pg.status(PlaygroundRing.SENSOR).flood_faulted is True
    assert pg.capabilities(PlaygroundRing.SENSOR).has_camera is False


def test_missing_token_says_where_to_get_one(tmp_path):
    pg = _pg(tmp_path, None)
    with pytest.raises(Unauthorized) as e:
        pg._token()
    assert "developer console" in str(e.value.detail)


def test_settings_turn_off_download_fallback_for_playground(monkeypatch):
    monkeypatch.setenv("MODE", "playground")
    s = Settings.from_env()
    assert s.is_playground and not s.is_mock
    assert s.capture_download_fallback is False
    assert s.dev_tools is True


def test_simulated_sensor_is_flagged_in_integrity():
    inc = {"id": "i", "opened_at_ms": 1000, "closed_at_ms": 5000, "status": "closed", "opened_source": "synthetic",
           "notes": {"simulated_sensor": True}}
    out = compute(inc, frames=[], health=[], captures=[], events=[], rover_log=[])
    assert any(f["kind"] == "simulated_sensor" for f in out["flags"])

def test_no_mock_captions_outside_mock_mode(tmp_path):
    from watermark.captions import MockCaptioner, make_captioner
    assert make_captioner(Settings(mode="playground", data_dir=tmp_path)) is None
    assert make_captioner(Settings(mode="live", data_dir=tmp_path)) is None
    assert isinstance(make_captioner(Settings(mode="mock", data_dir=tmp_path)), MockCaptioner)


def test_replay_is_read_only(monkeypatch):
    """The judged link serves recorded runs: no test endpoints, no background calls to Ring."""
    from watermark.config import Settings
    monkeypatch.setenv("MODE", "playground")
    monkeypatch.setenv("REPLAY", "1")
    s = Settings.from_env()
    assert s.replay and s.is_playground and not s.dev_tools
    monkeypatch.delenv("REPLAY")
    assert Settings.from_env().dev_tools

def test_replay_refuses_every_write(tmp_path, monkeypatch):
    """A judge clicking Delete everything on the replay link must not erase the recorded runs."""
    from fastapi.testclient import TestClient
    from watermark.app import create_app
    from watermark.config import Settings
    monkeypatch.setenv("MODE", "playground")
    monkeypatch.setenv("REPLAY", "1")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with TestClient(create_app(Settings.from_env())) as c:
        assert c.get("/api/account").status_code == 200
        for method, path in [("delete", "/api/account"), ("post", "/api/incidents/x/pack"),
                             ("post", "/api/incidents/x/close"), ("post", "/api/test/trigger")]:
            r = getattr(c, method)(path)
            assert r.status_code == 403 and "read-only" in r.json()["detail"], (method, path, r.status_code)