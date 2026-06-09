"""Thin wrapper around Apple Vision OCR via ocrmac.

Returns a list of OcrToken objects (text + confidence + pixel bbox)
suitable for spatial reasoning in parse.py.

`ocrmac` is macOS-only. Import is lazy so the rest of the CLI can run
(e.g. for `render`, `review`) on other platforms or in CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OcrToken:
    text: str
    confidence: float
    # Normalised (0..1) ocrmac bbox: (x, y, w, h) with origin at bottom-left.
    x: float
    y: float
    w: float
    h: float

    @property
    def x_centre(self) -> float:
        return self.x + self.w / 2

    @property
    def y_centre(self) -> float:
        # Flip so larger y = lower on the page (intuitive top-to-bottom order).
        return 1.0 - (self.y + self.h / 2)


def ocr_image(path: Path) -> list[OcrToken]:
    """Run Apple Vision OCR and return ordered tokens (top-to-bottom, left-to-right)."""
    try:
        from ocrmac import ocrmac
    except ImportError as e:  # pragma: no cover - platform guard
        raise RuntimeError(
            "ocrmac is required for OCR. Install with: pip install '.[mac]'  (macOS only)"
        ) from e

    raw = ocrmac.OCR(
        str(path),
        recognition_level="accurate",
        language_preference=["en-US"],
    ).recognize()

    tokens = [
        OcrToken(text=text, confidence=conf, x=bbox[0], y=bbox[1], w=bbox[2], h=bbox[3])
        for text, conf, bbox in raw
    ]
    tokens.sort(key=lambda t: (round(t.y_centre, 3), t.x_centre))
    return tokens


def cluster_rows(tokens: list[OcrToken], band_height: float = 0.012) -> list[list[OcrToken]]:
    """Group tokens that fall within `band_height` (normalised) of each other into rows."""
    rows: list[list[OcrToken]] = []
    for tok in sorted(tokens, key=lambda t: t.y_centre):
        if rows and abs(tok.y_centre - rows[-1][0].y_centre) <= band_height:
            rows[-1].append(tok)
        else:
            rows.append([tok])
    for r in rows:
        r.sort(key=lambda t: t.x_centre)
    return rows
