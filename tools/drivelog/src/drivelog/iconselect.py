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

import re
from pathlib import Path

from PIL import Image, ImageStat

from .ocr import OcrToken

ICON_OFFSET_RANGE = (0.02, 0.08)
ICON_OFFSET_STEPS = 7
SAMPLE_BOX_PX = 32
SELECTED_GAP_THRESHOLD = 80
PIXEL_BLUE_THRESHOLD = 30
PIXEL_BRIGHTNESS_MIN = 120


def _label_token(tokens: list[OcrToken], label: str) -> OcrToken | None:
    """Find the token whose text matches `label`, or synthesise one from a merged row.

    Apple Vision sometimes joins adjacent same-line labels into a single token
    (e.g. 'Quiet Street Main Road Multi-laned'). When the exact label isn't a
    standalone token, search for it as a word-bounded substring of any token
    and return a virtual OcrToken positioned at the matching X-slice of the
    parent. Word boundaries prevent 'Sealed' from matching inside 'Unsealed'.
    """
    norm = label.strip().lower()
    for t in tokens:
        if t.text.strip().lower() == norm:
            return t

    pattern = re.compile(rf"\b{re.escape(norm)}\b", re.IGNORECASE)
    for t in tokens:
        text = t.text.strip()
        m = pattern.search(text.lower())
        if not m:
            continue
        n_chars = len(text)
        if n_chars == 0:
            continue
        sub_x = t.x + (m.start() / n_chars) * t.w
        sub_w = (len(norm) / n_chars) * t.w
        return OcrToken(
            text=label,
            confidence=t.confidence,
            x=sub_x,
            y=t.y,
            w=sub_w,
            h=t.h,
        )
    return None


def _is_pastel_blue(r: float, g: float, b: float) -> bool:
    """True for the light selected-circle blue, false for dark raindrops, yellow suns, or white glyphs.

    Combines hue (blue dominant) and brightness (must be light) so dark blues
    inside unselected rain icons don't false-positive and yellow suns inside
    selected weather icons don't subtract from the score.
    """
    return (b - (r + g) / 2) > PIXEL_BLUE_THRESHOLD and (r + g + b) / 3 > PIXEL_BRIGHTNESS_MIN


def _blue_pixel_count(img: Image.Image, token: OcrToken) -> int:
    """Best count of pastel-blue pixels in a vertical strip of sample boxes above the label.

    Counting per-pixel decouples the selection signal from the icon glyph's
    own colour: a yellow sun on a blue background still has lots of blue
    pixels even though its mean is dragged down by the yellow.
    """
    w, h = img.size
    cx_px = int(token.x_centre * w)
    label_top_topdown = 1.0 - (token.y + token.h)
    label_top_px = int(label_top_topdown * h)

    half = SAMPLE_BOX_PX // 2
    lo, hi = ICON_OFFSET_RANGE
    best = 0
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
        data = region.tobytes()
        count = sum(
            1 for i in range(0, len(data), 3)
            if _is_pastel_blue(data[i], data[i + 1], data[i + 2])
        )
        if count > best:
            best = count
    return best


SELECTED_BLUENESS_MIN = 120


def detect_selected(
    image_path: Path,
    options: tuple[str, ...],
    tokens: list[OcrToken],
) -> str | None:
    """Single-select: return the most-blue option, or None if ambiguous."""
    img = Image.open(image_path)
    scored: list[tuple[str, float]] = []
    for option in options:
        token = _label_token(tokens, option)
        if token is None:
            continue
        scored.append((option, _blue_pixel_count(img, token)))
    if not scored:
        return None
    best_label, best_score = max(scored, key=lambda x: x[1])
    others = [s for lbl, s in scored if lbl != best_label]
    if others and best_score - max(others) < SELECTED_GAP_THRESHOLD:
        return None
    return best_label


def detect_multiple_selected(
    image_path: Path,
    options: tuple[str, ...],
    tokens: list[OcrToken],
    threshold: float = SELECTED_BLUENESS_MIN,
) -> list[str]:
    """Multi-select: every option whose icon background exceeds `threshold`.

    Used for rows like 'What kind of roads did you drive on?' where the
    user can tick more than one option.
    """
    img = Image.open(image_path)
    selected: list[str] = []
    for option in options:
        token = _label_token(tokens, option)
        if token is None:
            continue
        if _blue_pixel_count(img, token) >= threshold:
            selected.append(option)
    return selected
