"""Image encoding + shared prompts for the damage-detection vision pass.

Backends (Claude / Ollama / mock) live in backends.py and share these.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

SYSTEM = (
    "You are a property-restoration estimator documenting renovation and "
    "insurance damage from a single photograph. You are precise and conservative: "
    "you report only damage you can actually see, you never invent findings, and "
    "when a photo shows an intact, undamaged area you say so and return no findings. "
    "You think like an adjuster writing a scope of work: each finding names the "
    "affected materials and a concrete remediation action a contractor could price."
)

PROMPT = (
    "Analyze this photo of a property that experienced a water/flood incident. "
    "Identify every distinct, visible damage finding (water intrusion, staining, "
    "mold, cracking, warping, delamination, etc.). For each, note the area, the "
    "affected materials, a severity (none/minor/moderate/severe), your confidence "
    "(low/medium/high) that the finding is real, and the concrete remediation action. "
    "Keep the description and the remediation action in their separate fields; do not "
    "repeat the remediation inside the description. If the photo shows no relevant "
    "damage, set is_damage_visible to false and return an empty findings list. "
    "Respond only with the structured data."
)


def encode_image(path: Path, max_dim: int = 1536, quality: int = 85) -> str:
    """Downscale + re-encode to JPEG base64 to keep vision token cost sane.

    Source phone photos are often 3-4 MB / 4000px; a 1536px long edge is plenty
    for damage classification and roughly caps image tokens. Returns raw base64
    (no data: prefix) — suitable for both the Claude and Ollama image fields.
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # honor phone rotation
    img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")
