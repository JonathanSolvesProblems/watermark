"""Pluggable damage-analysis backends + a content-addressed cache.

From the RenoScout Phase 0 brain, which was verified on the real June 2026 flood
photos (16 photos, 26 findings). Backends all return (ImageAnalysis | None, usage):

  - mock    : canned findings, zero calls. For pipeline and report development.
  - bedrock : Amazon Bedrock Converse API (AWS Builder mini-challenge). Default Nova Lite.
  - ollama  : local open vision model via the Ollama HTTP API. Free, on-GPU.
  - claude  : Anthropic API, client.messages.parse.

The cache is keyed by a hash of (backend, model, max_dim, image bytes), so any
photo is analysed at most once per (backend, model).
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

from .damage_vision import PROMPT, SYSTEM, encode_image
from .schema import ImageAnalysis

CLAUDE_DEFAULT = "claude-opus-4-8"
OLLAMA_DEFAULT = "qwen2.5vl:7b"
BEDROCK_DEFAULT = "amazon.nova-lite-v1:0"
OLLAMA_HOST = "http://localhost:11434"

CLAUDE_PRICING = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def default_model(backend: str) -> str:
    return {"claude": CLAUDE_DEFAULT, "ollama": OLLAMA_DEFAULT, "bedrock": BEDROCK_DEFAULT, "mock": "mock"}[backend]


class MockBackend:
    """Deterministic fake findings from the filename. Filenames containing
    'clean'/'ok'/'intact' come back undamaged; everything else gets one finding."""

    name = "mock"
    model = "mock"

    def analyze(self, path: Path, max_dim: int = 1536):
        stem = path.stem.lower()
        if any(k in stem for k in ("clean", "ok", "intact", "undamaged")):
            return ImageAnalysis(is_damage_visible=False, summary="Mock: area appears intact.", findings=[]), {}
        h = int(hashlib.sha256(path.name.encode()).hexdigest(), 16)
        severity = ["minor", "moderate", "severe"][h % 3]
        area = path.stem.replace("_", " ").replace("-", " ")[:40] or "Unknown area"
        finding = {
            "area": area, "damage_type": "water intrusion", "severity": severity, "confidence": "low",
            "affected_materials": ["drywall", "baseboard"],
            "description": "MOCK finding for offline pipeline testing (no model was run).",
            "recommended_action": "Remove and replace affected drywall/baseboard; dry the cavity.",
        }
        return ImageAnalysis(is_damage_visible=True, summary="Mock: one finding.", findings=[finding]), {}


class BedrockBackend:
    """Bedrock Converse with an image block and a JSON-only instruction, validated
    against the Pydantic schema. Any vision-capable Bedrock model works."""

    name = "bedrock"

    def __init__(self, model: str, region: str = "us-east-1"):
        import boto3  # lazy
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model = model

    def analyze(self, path: Path, max_dim: int = 1536):
        import base64
        jpeg = base64.b64decode(encode_image(path, max_dim=max_dim))
        schema = json.dumps(ImageAnalysis.model_json_schema())
        resp = self.client.converse(
            modelId=self.model,
            system=[{"text": SYSTEM}],
            messages=[{"role": "user", "content": [
                {"image": {"format": "jpeg", "source": {"bytes": jpeg}}},
                {"text": PROMPT + "\nReturn only a JSON object matching this schema, no prose:\n" + schema},
            ]}],
            inferenceConfig={"maxTokens": 1500, "temperature": 0},
        )
        text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"]).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        analysis = ImageAnalysis.model_validate_json(text[start:end + 1] if start != -1 else text)
        usage = resp.get("usage", {})
        return analysis, {"input_tokens": usage.get("inputTokens", 0), "output_tokens": usage.get("outputTokens", 0)}


class ClaudeBackend:
    name = "claude"

    def __init__(self, model: str):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model

    def analyze(self, path: Path, max_dim: int = 1536):
        b64 = encode_image(path, max_dim=max_dim)
        resp = self.client.messages.parse(
            model=self.model, max_tokens=4096, system=SYSTEM,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": PROMPT},
            ]}],
            output_format=ImageAnalysis,
        )
        usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0),
                 "output_tokens": getattr(resp.usage, "output_tokens", 0)}
        return resp.parsed_output, usage


class OllamaBackend:
    name = "ollama"

    def __init__(self, model: str, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host.rstrip("/")

    def analyze(self, path: Path, max_dim: int = 1536):
        b64 = encode_image(path, max_dim=max_dim)
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": PROMPT, "images": [b64]}],
            "stream": False,
            "format": ImageAnalysis.model_json_schema(),
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(f"{self.host}/api/chat", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"Could not reach Ollama at {self.host} ({e}). Try: ollama pull {self.model}") from e
        analysis = ImageAnalysis.model_validate_json(body.get("message", {}).get("content", ""))
        return analysis, {"input_tokens": body.get("prompt_eval_count", 0), "output_tokens": body.get("eval_count", 0)}


def get_backend(name: str, model: str | None = None, region: str = "us-east-1"):
    model = model or default_model(name)
    if name == "mock":
        return MockBackend()
    if name == "bedrock":
        return BedrockBackend(model, region)
    if name == "ollama":
        return OllamaBackend(model)
    if name == "claude":
        return ClaudeBackend(model)
    raise ValueError(f"unknown backend: {name}")


def _cache_key(backend: str, model: str, max_dim: int, path: Path) -> str:
    h = hashlib.sha256()
    h.update(f"{backend}|{model}|{max_dim}|".encode())
    h.update(path.read_bytes())
    return h.hexdigest()


def cached_analyze(backend_obj, path: Path, max_dim: int, cache_dir: Path, use_cache: bool):
    """Return (analysis, usage, cache_hit). Persists results so re-runs are free."""
    key = _cache_key(backend_obj.name, getattr(backend_obj, "model", "mock"), max_dim, path)
    cache_file = cache_dir / f"{key}.json"
    if use_cache and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return ImageAnalysis.model_validate(data["analysis"]), data.get("usage", {}), True
        except Exception:  # noqa: BLE001
            pass
    analysis, usage = backend_obj.analyze(path, max_dim=max_dim)
    if use_cache and analysis is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"analysis": analysis.model_dump(), "usage": usage}, indent=2),
                              encoding="utf-8")
    return analysis, usage, False
