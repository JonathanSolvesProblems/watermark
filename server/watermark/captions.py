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


def make_captioner(settings) -> Captioner:
    if settings.captions_backend == "bedrock":
        return BedrockCaptioner(settings.bedrock_model_id, settings.aws_region)
    return MockCaptioner()


def narrative(incident: dict, frames: list[dict], readings: list[dict], integrity: dict, settings) -> str:
    """A short plain-language narrative for the pack. Bedrock when configured,
    otherwise a deterministic template built from the same data."""
    opened = incident.get("opened_at_ms")
    closed = incident.get("closed_at_ms")
    dur = f"{(closed - opened) / 60000:.0f} minutes" if opened and closed else "an open incident"
    n_water = sum(1 for f in frames if f.get("water_visible"))
    template = (
        f"A Ring {incident.get('kind', 'flood')} sensor in the {incident.get('room') or 'unnamed room'} reported "
        f"{'water' if incident.get('kind') == 'flood' else 'a freeze condition'} and the incident lasted {dur}. "
        f"{len(frames)} frames were captured from a Ring camera; a vision model judged water visible in {n_water} of them. "
        f"{len(readings)} environmental readings were logged. "
        f"The integrity section lists {len(integrity.get('gaps', []))} gap(s) and {len(integrity.get('flags', []))} flag(s). "
        "This narrative describes captured evidence only and makes no claim about the cause."
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
