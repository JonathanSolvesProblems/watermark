"""Structured output schema for the damage-detection vision pass.

These Pydantic models are handed to client.messages.parse(output_format=...),
which forces Claude to return JSON that validates against them. Keep the schema
flat and avoid unsupported JSON-schema constraints (minItems, recursion, etc.).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["none", "minor", "moderate", "severe"]
Confidence = Literal["low", "medium", "high"]


class DamageFinding(BaseModel):
    """One distinct problem visible in a single photo."""

    area: str = Field(
        description="Room or location, best guess from the image, e.g. "
        "'Basement — north wall' or 'Bathroom floor'."
    )
    damage_type: str = Field(
        description="Short category, e.g. 'water intrusion', 'mold', 'crack', "
        "'delamination', 'staining', 'warping'."
    )
    severity: Severity = Field(
        description="none, minor, moderate, or severe — from a restoration standpoint."
    )
    confidence: Confidence = Field(
        description="How sure you are this finding is real and correctly categorized "
        "from what is actually visible: low, medium, or high."
    )
    affected_materials: list[str] = Field(
        description="Materials involved, e.g. ['drywall', 'baseboard', 'carpet']."
    )
    description: str = Field(
        description="One or two plain sentences on what is visible and why it matters."
    )
    recommended_action: str = Field(
        description="Concrete remediation step a contractor would quote, e.g. "
        "'Remove and replace the lower 2 ft of water-damaged drywall and baseboard.'"
    )


class ImageAnalysis(BaseModel):
    """Whole-image result. `findings` is empty when nothing is wrong."""

    is_damage_visible: bool = Field(
        description="True if any renovation/insurance-relevant damage is visible."
    )
    summary: str = Field(
        description="One-sentence summary of the photo for a human reviewer."
    )
    findings: list[DamageFinding] = Field(
        description="Every distinct damage finding in this photo. Empty if none."
    )
