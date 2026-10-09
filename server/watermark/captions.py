"""Frame captions. Bedrock (AWS Builder mini-challenge) or a deterministic mock.

The caption is conservative on purpose: it says what is visible and gives a
rough extent, and it never guesses the cause. The pack's integrity section
carries the model id so a reader knows a model wrote it.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass

PROMPT = (
    "You are documenting a possible water incident inside a home from a single camera frame, "
    "for an insurance evidence file. Describe only what is visible. If water or wetness is visible, "
    "say where (floor, baseboard, wall, ceiling, object) and estimate its extent conservatively "
    "(for example 'a thin film along the baseboard' or 'roughly 1 to 2 cm deep near the water heater'). "
    "Never state a cause. If nothing wet is visible, say so plainly. "
    "Respond with JSON only: {\"description\": string, \"water_visible\": boolean, "
    "\"extent\": string, \"confidence\": \"low\"|\"medium\"|\"high\"}"
)


@dataclass
class Caption:
    description: str
    water_visible: bool
    extent: str
    confidence: str
    model: str


class Captioner:
    def caption(self, jpeg: bytes, context: str = "") -> Caption:
        raise NotImplementedError


class MockCaptioner(Captioner):
    def caption(self, jpeg: bytes, context: str = "") -> Caption:
        return Caption(
            description="MOCK caption: synthetic frame, a blue band across the floor near the water heater.",
            water_visible=True, extent="synthetic band, extent not meaningful", confidence="low", model="mock")


class BedrockCaptioner(Captioner):
    """Amazon Bedrock Converse API with an image block. Default model is Nova Lite;
    any Bedrock model with vision works (set BEDROCK_MODEL_ID)."""

    def __init__(self, model_id: str, region: str):
        import boto3  # lazy
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def caption(self, jpeg: bytes, context: str = "") -> Caption:
        text = PROMPT + (f"\nContext: {context}" if context else "")
        resp = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [
                {"image": {"format": "jpeg", "source": {"bytes": jpeg}}},
                {"text": text},
            ]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0},
        )
        out = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
        data = _extract_json(out)
        return Caption(
            description=str(data.get("description", out.strip()))[:600],
            water_visible=bool(data.get("water_visible", False)),
            extent=str(data.get("extent", ""))[:200],
            confidence=str(data.get("confidence", "low")),
            model=self.model_id,
        )


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {"description": text}


def make_captioner(settings) -> Captioner | None:
    """Bedrock when configured. The mock captioner describes the synthetic mock frame,
    so it is only ever used in mock mode: on a real Ring frame its text would be false.
    Anywhere else without Bedrock, frames stay uncaptioned and say so."""
    if settings.captions_backend == "bedrock":
        return BedrockCaptioner(settings.bedrock_model_id, settings.aws_region)
    if settings.is_mock:
        return MockCaptioner()
    return None


def _n(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _span(ms: int) -> str:
    s = max(0, round(ms / 1000))
    if s < 90:
        return _n(s, "second")
    m = round(s / 60)
    return _n(m, "minute") if m < 90 else f"{m // 60} h {m % 60:02d} min"


def narrative(incident: dict, frames: list[dict], readings: list[dict], integrity: dict, settings) -> str:
    """A short plain-language narrative for the pack. Bedrock when configured,
    otherwise a deterministic template built from the same data."""
    opened = incident.get("opened_at_ms")
    closed = incident.get("closed_at_ms")
    room = incident.get("room") or "an unnamed room"
    what = "Water reached" if incident.get("kind") == "flood" else "Freezing reached"
    stood = f" and stood for {_span(closed - opened)}" if opened is not None and closed is not None else ", and it is still there"
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    captioned = [f for f in frames if f.get("water_visible") is not None]
    n_water = sum(1 for f in captioned if f.get("water_visible"))
    first = min((f["media_ms"] for f in frames if f.get("media_ms")), default=None)
    if not frames:
        seen = "No frame came from a Ring camera."
    else:
        seen = f"The Ring camera sent {_n(len(frames), 'frame')}"
        seen += f", the first {max(0, first - opened) / 1000:.1f} s after the sensor." if first is not None and opened is not None else "."
        nc = len(captioned)
        if nc:
            which = ("both frames it described" if nc == 2 and n_water == 2 else
                     f"all {nc} frames it described" if n_water == nc else f"{n_water} of the {nc} frames it described")
            seen += f" The captions saw water in {which}." if n_water else " The captions saw no water."
        else:
            seen += " None of them is captioned."
    gaps, flags = len(integrity.get("gaps", [])), len(integrity.get("flags", []))
    count = lambda n, noun: f"{words.get(n, n)} {noun}{'' if n == 1 else 's'}".capitalize()
    if gaps or flags:
        parts = [count(gaps, "gap")] if gaps else []
        parts += [("one note" if flags == 1 else f"{words.get(flags, flags)} notes")] if flags else []
        vouch = f"{' and '.join(parts)[0].upper()}{' and '.join(parts)[1:]} {'is' if gaps + flags == 1 else 'are'} listed below."
    else:
        vouch = "Nothing is missing from the record."
    rooms = f" {count(len(readings), 'room reading')} {'was' if len(readings) == 1 else 'were'} logged." if readings else ""
    template = (
        f"{what} the sensor in {room}{stood}. {seen}{rooms} {vouch} "
        "This describes what was recorded, not what caused it."
    )
    if settings.captions_backend != "bedrock":
        return template
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        facts = json.dumps({"incident": {k: incident.get(k) for k in ("kind", "room", "opened_at_ms", "closed_at_ms",
                                                                        "opened_source", "closed_source")},
                            "frames": [{"media_ms": f.get("media_ms"), "caption": f.get("caption"),
                                        "water_visible": f.get("water_visible")} for f in frames][:20],
                            "readings": readings[:40], "integrity": integrity})
        resp = client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text":
                "Write a 120 to 180 word factual narrative of this home water incident for an insurance evidence file. "
                "Use only the facts given. State times, what the camera showed, what the sensors logged, and what could not "
                "be verified. Do not speculate about the cause. Plain prose, no bullet points.\n\n" + facts}]}],
            inferenceConfig={"maxTokens": 500, "temperature": 0},
        )
        return "".join(b.get("text", "") for b in resp["output"]["message"]["content"]).strip() or template
    except Exception:  # noqa: BLE001
        return template
