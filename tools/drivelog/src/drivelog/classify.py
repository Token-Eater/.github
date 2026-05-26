"""Decide whether a screenshot is a trip-detail page (A) or conditions page (B)."""

from __future__ import annotations

from enum import Enum

from .ocr import OcrToken


class ScreenKind(str, Enum):
    DETAIL = "detail"
    CONDITIONS = "conditions"
    UNKNOWN = "unknown"


DETAIL_MARKERS = ("Odometer", "Vehicle", "Start Suburb", "End Suburb")
CONDITIONS_MARKERS = ("weather", "traffic", "road", "feel")


def classify(tokens: list[OcrToken]) -> ScreenKind:
    text_blob = " ".join(t.text for t in tokens).lower()
    detail_hits = sum(1 for m in DETAIL_MARKERS if m.lower() in text_blob)
    cond_hits = sum(1 for m in CONDITIONS_MARKERS if m in text_blob)
    if detail_hits >= 2 and detail_hits > cond_hits:
        return ScreenKind.DETAIL
    if cond_hits >= 2 and cond_hits > detail_hits:
        return ScreenKind.CONDITIONS
    return ScreenKind.UNKNOWN
