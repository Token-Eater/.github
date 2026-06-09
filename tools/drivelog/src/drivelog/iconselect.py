"""Detect which option is selected on the conditions screen.

The icon for each option is a circle above its text label. Selected
options have a light-blue background; unselected are dark grey. OCR
can't see colour, but we can sample pixels above each label's bounding
box to figure out which icon is "lit up".

We score by "blueness" = B - (R+G)/2 so the light-blue selected circle
stands out from both dark-grey unselected backgrounds and white icon
glyphs (sun, cloud, snowflake) inside the circle.

Icon-to-label spacing varies between rows (3-option rows have bigger
icons than 5-option rows), so for each label we sample a vertical strip
of Y positions above it and take whichever sample has the highest
blueness.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat

from .ocr import OcrToken

ICON_OFFSET_RANGE = (0.02, 0.08)
ICON_OFFSET_STEPS = 7
SAMPLE_BOX_PX = 24
SELECTED_GAP_THRESHOLD = 15


def _label_token(tokens: list[OcrToken], label: str) -> OcrToken | None:
    norm = label.strip().lower()
    for t in tokens:
        if t.text.strip().lower() == norm:
            return t
    return None


def _blueness_above(img: Image.Image, token: OcrToken) -> float:
    """Best blueness score in a vertical strip above the label's bbox."""
    w, h = img.size
    cx_px = int(token.x_centre * w)
    label_top_topdown = 1.0 - (token.y + token.h)
    label_top_px = int(label_top_topdown * h)

    half = SAMPLE_BOX_PX // 2
    lo, hi = ICON_OFFSET_RANGE
    best = -float("inf")
    for i in range(ICON_OFFSET_STEPS):
        offset_frac = lo + (hi - lo) * i / (ICON_OFFSET_STEPS - 1)
        icon_centre_y_px = label_top_px - int(offset_frac * h)
        box = (
            max(0, cx_px - half),
            max(0, icon_centre_y_px - half),
            min(w, cx_px + half),
            min(h, icon_centre_y_px + half),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        region = img.crop(box).convert("RGB")
        r, g, b = ImageStat.Stat(region).mean
        blueness = b - (r + g) / 2
        if blueness > best:
            best = blueness
    return best if best != -float("inf") else 0.0


def detect_selected(
    image_path: Path,
    options: tuple[str, ...],
    tokens: list[OcrToken],
) -> str | None:
    """Return the option whose icon background is most blue, or None if ambiguous."""
    img = Image.open(image_path)
    scored: list[tuple[str, float]] = []
    for option in options:
        token = _label_token(tokens, option)
        if token is None:
            continue
        scored.append((option, _blueness_above(img, token)))
    if not scored:
        return None
    best_label, best_score = max(scored, key=lambda x: x[1])
    others = [s for lbl, s in scored if lbl != best_label]
    if others and best_score - max(others) < SELECTED_GAP_THRESHOLD:
        return None
    return best_label
