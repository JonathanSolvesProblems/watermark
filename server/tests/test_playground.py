"""Playground mode: the simulated sensor and its labelling, without touching the network."""
import pytest
from ringpartner import Unauthorized

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
