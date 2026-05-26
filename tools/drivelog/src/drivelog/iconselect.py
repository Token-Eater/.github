"""Detect which option is selected on the conditions screen.

The icon for each option is a circle above its text label. Selected
options have a light-blue background; unselected are dark grey. OCR
can't see colour, but we can sample pixels above each label's bounding
box to figure out which icon is "lit up".

The label tokens come from OCR. For each option label we:
1. Convert the label's bbox to pixel coords (ocrmac origin is bottom-left, normalised).
2. Sample a small box centred above the label, where the icon sits.
3. Score by mean brightness: selected (light blue) is much brighter than
   unselected (dark grey).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat

from .ocr import OcrToken

ICON_OFFSET_REL_TO_IMG = 0.04
SAMPLE_BOX_PX = 24


def _label_token(tokens: list[OcrToken], label: str) -> OcrToken | None:
    norm = label.strip().lower()
    for t in tokens:
        if t.text.strip().lower() == norm:
            return t
    return None


def _sample_above(img: Image.Image, token: OcrToken) -> tuple[float, float, float]:
    w, h = img.size
    cx_px = int(token.x_centre * w)
    label_top_topdown = 1.0 - (token.y + token.h)
    icon_centre_y_px = int(label_top_topdown * h) - int(ICON_OFFSET_REL_TO_IMG * h)

    half = SAMPLE_BOX_PX // 2
    box = (
        max(0, cx_px - half),
        max(0, icon_centre_y_px - half),
        min(w, cx_px + half),
        min(h, icon_centre_y_px + half),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        return (0.0, 0.0, 0.0)
    region = img.crop(box).convert("RGB")
    r, g, b = ImageStat.Stat(region).mean
    return (r, g, b)


def detect_selected(
    image_path: Path,
    options: tuple[str, ...],
    tokens: list[OcrToken],
) -> str | None:
    """Return the option whose icon region is brightest, or None if undetectable."""
    img = Image.open(image_path)
    scored: list[tuple[str, float]] = []
    for option in options:
        token = _label_token(tokens, option)
        if token is None:
            continue
        r, g, b = _sample_above(img, token)
        brightness = (r + g + b) / 3
        scored.append((option, brightness))
    if not scored:
        return None
    best_label, best_score = max(scored, key=lambda x: x[1])
    # Require a meaningful gap between the brightest and the next: otherwise
    # the screenshot is ambiguous and we should defer to the review step.
    others = [s for lbl, s in scored if lbl != best_label]
    if others and best_score - max(others) < 20:
        return None
    return best_label
