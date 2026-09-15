"""Library entry point used by the server, and the shared core of the CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .backends import cached_analyze, get_backend

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def analyze_paths(paths: list[Path], backend: str = "mock", model: str | None = None, max_dim: int = 1536,
                  cache_dir: Path | None = None, use_cache: bool = True, bedrock_region: str = "us-east-1",
                  on_progress=None) -> list[dict[str, Any]]:
    """Analyse each image. Returns [{"photo", "analysis": dict, "usage", "cached"}]."""
    be = get_backend(backend, model, region=bedrock_region)
    cache = cache_dir or Path(__file__).with_name(".cache")
    out: list[dict[str, Any]] = []
    for i, p in enumerate(paths, 1):
        try:
            analysis, usage, hit = cached_analyze(be, Path(p), max_dim, cache, use_cache)
        except Exception as e:  # noqa: BLE001
            if on_progress:
                on_progress(i, len(paths), Path(p).name, f"FAILED ({e})")
            continue
        if analysis is None:
            continue
        if on_progress:
            n = len(analysis.findings)
            on_progress(i, len(paths), Path(p).name, "cached" if hit else ("clean" if n == 0 else f"{n} finding(s)"))
        out.append({"photo": Path(p).name, "path": str(p), "analysis": analysis.model_dump(), "usage": usage,
                    "cached": hit})
    return out
