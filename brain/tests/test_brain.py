from pathlib import Path

from PIL import Image

from watermark_brain import analyze_paths
from watermark_brain.cli import main
from watermark_brain.report import ImageResult, build_markdown
from watermark_brain.schema import ImageAnalysis


def _img(p: Path, shade: int | None = None) -> Path:
    # Distinct bytes per file: the cache is content-addressed, so two identical
    # images are (correctly) one analysis.
    s = shade if shade is not None else (sum(p.name.encode()) % 200) + 20
    Image.new("RGB", (64, 48), (s, s, s)).save(p, format="JPEG")
    return p


def test_mock_backend_and_cache(tmp_path):
    a = _img(tmp_path / "basement_wall.jpg")
    b = _img(tmp_path / "hall_clean.jpg")
    res = analyze_paths([a, b], backend="mock", cache_dir=tmp_path / ".cache")
    assert len(res) == 2 and not res[0]["cached"]
    assert res[0]["analysis"]["is_damage_visible"] and res[0]["analysis"]["findings"][0]["damage_type"] == "water intrusion"
    assert not res[1]["analysis"]["is_damage_visible"]
    again = analyze_paths([a, b], backend="mock", cache_dir=tmp_path / ".cache")
    assert all(r["cached"] for r in again)


def test_cli_writes_reports(tmp_path):
    d = tmp_path / "in"
    d.mkdir()
    _img(d / "water_heater.jpg")
    _img(d / "montage_scan.jpg")
    out = tmp_path / "out"
    rc = main(["--input", str(d), "--output", str(out), "--backend", "mock", "--exclude", "*scan*"])
    assert rc == 0
    assert (out / "scope-report.html").exists() and (out / "findings.json").exists()
    html = (out / "scope-report.html").read_text(encoding="utf-8")
    assert "water heater" in html and "montage" not in html


def test_markdown_skips_severity_none(tmp_path):
    p = _img(tmp_path / "x.jpg")
    analysis = ImageAnalysis(is_damage_visible=True, summary="s", findings=[
        {"area": "A", "damage_type": "staining", "severity": "none", "confidence": "high",
         "affected_materials": [], "description": "checked and clean", "recommended_action": "none"},
        {"area": "B", "damage_type": "water intrusion", "severity": "severe", "confidence": "high",
         "affected_materials": ["drywall"], "description": "wet", "recommended_action": "replace"},
    ])
    md = build_markdown([ImageResult(path=p, analysis=analysis)], "now")
    assert "B" in md and "checked and clean" not in md
