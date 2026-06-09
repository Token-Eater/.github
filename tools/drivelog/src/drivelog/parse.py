"""Parse spatial OCR tokens into TripDetail / TripConditions records.

The detail screen is a vertical list of "Label | Value" rows. We find each
known label by text, then take everything to its right on the same Y-band
as the value.

The conditions screen has icon-based selectors whose state is colour-only
(light-blue circle = selected, dark grey = unselected). OCR returns the
option text positions; iconselect.detect_selected samples pixels above
each label to figure out which is lit. If image_path isn't supplied the
selection is left as "Unknown" for the review step.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .config import TZ
from .model import TripConditions, TripDetail
from .ocr import OcrToken, cluster_rows

DETAIL_LABELS = (
    "Vehicle",
    "Supervisor",
    "Start Suburb",
    "End Suburb",
    "Start Time",
    "End Time",
    "Start Odometer",
    "End Odometer",
)


_HEADER_RE = re.compile(
    r"(\d{1,2}\s+\w+\s+\d{4})\s+(?:at\s+)?(\d{1,2}:\d{2}\s*(?:am|pm))",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


class ParseError(ValueError):
    pass


def parse_header_timestamp(tokens: list[OcrToken]) -> datetime:
    """The page-header timestamp is the topmost text matching '<date> at <time>'."""
    rows = cluster_rows(tokens)
    for row in rows[:6]:  # only look near the top
        joined = " ".join(t.text for t in row)
        m = _HEADER_RE.search(joined)
        if m:
            return _parse_datetime(m.group(1), m.group(2))
    raise ParseError("Could not find header timestamp")


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    cleaned = f"{date_str} {time_str.replace(' ', '').upper()}"
    for fmt in ("%d %B %Y %I:%M%p", "%d %b %Y %I:%M%p"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    raise ParseError(f"Could not parse datetime from {date_str!r} {time_str!r}")


def _extract_rows(tokens: list[OcrToken]) -> dict[str, str]:
    """Return {label: value} for each known DETAIL_LABEL present."""
    rows = cluster_rows(tokens)
    result: dict[str, str] = {}
    for row in rows:
        row_text = " ".join(t.text for t in row).strip()
        for label in DETAIL_LABELS:
            if row_text.lower().startswith(label.lower()):
                value = row_text[len(label):].strip().lstrip(":").strip()
                if value:
                    result[label] = value
                break
    return result


def _extract_signed_off(tokens: list[OcrToken]) -> str | None:
    for row in cluster_rows(tokens):
        text = " ".join(t.text for t in row)
        m = re.search(r"Signed off by\s+(.+?)(?:\s+\d{1,2}\s+\w+\s+\d{4}|$)", text)
        if m:
            return m.group(1).strip()
    return None


def _extract_day_night(tokens: list[OcrToken]) -> tuple[int, int, int]:
    """Find the 'Day HH:MM + Night HH:MM = Total HH:MM' summary."""
    text = " ".join(t.text for t in tokens)
    day = night = total = None
    for label, target in (("Day", "day"), ("Night", "night"), ("Total", "total")):
        m = re.search(rf"{label}\s*(\d{{1,2}}):(\d{{2}})", text)
        if m:
            mins = int(m.group(1)) * 60 + int(m.group(2))
            if target == "day":
                day = mins
            elif target == "night":
                night = mins
            else:
                total = mins
    if day is None or night is None or total is None:
        raise ParseError("Could not parse Day/Night/Total summary")
    return day, night, total


def parse_detail(tokens: list[OcrToken]) -> TripDetail:
    header = parse_header_timestamp(tokens)
    rows = _extract_rows(tokens)
    signed_off = _extract_signed_off(tokens)
    day_min, night_min, total_min = _extract_day_night(tokens)

    missing = [lbl for lbl in DETAIL_LABELS if lbl not in rows]
    if missing:
        raise ParseError(f"Missing fields in detail screenshot: {missing}")

    return TripDetail(
        header_timestamp=header,
        vehicle=rows["Vehicle"],
        supervisor_label=rows["Supervisor"],
        signed_off_by=signed_off,
        start_suburb=rows["Start Suburb"],
        end_suburb=rows["End Suburb"],
        start_time=_parse_value_datetime(rows["Start Time"]),
        end_time=_parse_value_datetime(rows["End Time"]),
        start_odometer=_parse_odometer(rows["Start Odometer"]),
        end_odometer=_parse_odometer(rows["End Odometer"]),
        day_minutes=day_min,
        night_minutes=night_min,
        total_minutes=total_min,
    )


def _parse_value_datetime(value: str) -> datetime:
    m = _HEADER_RE.search(value)
    if not m:
        raise ParseError(f"Could not parse datetime from {value!r}")
    return _parse_datetime(m.group(1), m.group(2))


def _parse_odometer(value: str) -> int:
    return int(re.sub(r"[^\d]", "", value))


# Conditions options as shown in-app (ordered as they appear left-to-right).
WEATHER_OPTIONS = ("Fine", "Rain", "Snow", "Icy", "Fog")
ROAD_OPTIONS = ("Sealed", "Unsealed", "Quiet Street", "Main Road", "Multi-laned")
TRAFFIC_OPTIONS = ("Light", "Moderate", "Heavy")
FEEL_OPTIONS = ("Awful", "Bad", "Meh", "Good", "Great")


def parse_conditions(tokens: list[OcrToken], image_path: Path | None = None) -> TripConditions:
    """Extract header timestamp, selection (via pixel sampling), and notes.

    If image_path is provided, sample icon regions to detect which option
    is selected. Otherwise leave selections as "Unknown" for review.
    """
    header = parse_header_timestamp(tokens)

    if image_path is not None:
        from .iconselect import detect_selected
        weather = detect_selected(image_path, WEATHER_OPTIONS, tokens) or "Unknown"
        road_type = detect_selected(image_path, ROAD_OPTIONS, tokens) or "Unknown"
        traffic = detect_selected(image_path, TRAFFIC_OPTIONS, tokens) or "Unknown"
        feel = detect_selected(image_path, FEEL_OPTIONS, tokens) or "Unknown"
    else:
        weather = road_type = traffic = feel = "Unknown"

    notes = _extract_notes(tokens)

    return TripConditions(
        header_timestamp=header,
        weather=weather,
        road_type=road_type,
        traffic=traffic,
        feel=feel,
        notes=notes,
    )


def _extract_notes(tokens: list[OcrToken]) -> str:
    """Anything below the 'Notes' label, joined into one string."""
    notes_token = next((t for t in tokens if t.text.strip().lower() == "notes"), None)
    if notes_token is None:
        return ""
    below = [t for t in tokens if t.y_centre > notes_token.y_centre + 0.005]
    below.sort(key=lambda t: (round(t.y_centre, 3), t.x_centre))
    return " ".join(t.text for t in below).strip()
