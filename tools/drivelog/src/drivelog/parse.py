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
from datetime import date, datetime, timedelta
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
_RELATIVE_HEADER_RE = re.compile(
    r"\b(Today|Yesterday)\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm))",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


class ParseError(ValueError):
    pass


def screenshot_date(image_path: Path | None) -> date:
    """Return the date the screenshot was captured, for resolving 'Today'/'Yesterday'.

    Uses file mtime (preserved by AirDrop in the common case) and falls
    back to the current date in ACT if the file can't be stat'd.
    """
    if image_path is not None:
        try:
            mtime = image_path.stat().st_mtime
            return datetime.fromtimestamp(mtime, tz=TZ).date()
        except OSError:
            pass
    return datetime.now(TZ).date()


def parse_header_timestamp(tokens: list[OcrToken], base_date: date | None = None) -> datetime:
    """The page-header timestamp is the topmost text matching an absolute or relative date."""
    rows = cluster_rows(tokens)
    for row in rows[:8]:
        joined = " ".join(t.text for t in row)
        try:
            return _parse_datetime_from_text(joined, base_date)
        except ParseError:
            continue
    raise ParseError("Could not find header timestamp")


def _parse_datetime_from_text(text: str, base_date: date | None) -> datetime:
    """Try absolute ('6 Jun 2026 at 2:42 pm') then relative ('Today at 3:34 am')."""
    m = _HEADER_RE.search(text)
    if m:
        return _parse_absolute_datetime(m.group(1), m.group(2))
    m = _RELATIVE_HEADER_RE.search(text)
    if m:
        if base_date is None:
            base_date = datetime.now(TZ).date()
        word = m.group(1).lower()
        anchor = base_date - timedelta(days=1) if word == "yesterday" else base_date
        return _combine_date_and_time_str(anchor, m.group(2))
    raise ParseError(f"Could not parse datetime from {text!r}")


def _parse_absolute_datetime(date_str: str, time_str: str) -> datetime:
    cleaned = f"{date_str} {time_str.replace(' ', '').upper()}"
    for fmt in ("%d %B %Y %I:%M%p", "%d %b %Y %I:%M%p"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    raise ParseError(f"Could not parse datetime from {date_str!r} {time_str!r}")


def _combine_date_and_time_str(d: date, time_str: str) -> datetime:
    cleaned = time_str.replace(" ", "").upper()
    t = datetime.strptime(cleaned, "%I:%M%p").time()
    return datetime.combine(d, t).replace(tzinfo=TZ)


_TRAILING_CHEVRONS = ">›❯→"


def _strip_chevron(s: str) -> str:
    """Strip the iOS tappable-row chevron that OCR sometimes captures (>, ›, etc)."""
    s = s.strip()
    while s and s[-1] in _TRAILING_CHEVRONS:
        s = s[:-1].strip()
    return s


def _extract_rows(tokens: list[OcrToken]) -> dict[str, str]:
    """Return {label: value} for each known DETAIL_LABEL present."""
    rows = cluster_rows(tokens)
    result: dict[str, str] = {}
    for row in rows:
        row_text = " ".join(t.text for t in row).strip()
        for label in DETAIL_LABELS:
            if row_text.lower().startswith(label.lower()):
                value = row_text[len(label):].strip().lstrip(":").strip()
                value = _strip_chevron(value)
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


_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _extract_day_night(tokens: list[OcrToken]) -> tuple[int, int, int]:
    """Find the 'Day HH:MM + Night HH:MM = Total HH:MM' summary box.

    Labels and values are on separate visual rows. Prefer spatial lookup
    (find a HH:MM token below each label in the same column), and fall
    back to flat-text regex if that fails.
    """
    results: dict[str, int] = {}
    for label_text in ("Day", "Night", "Total"):
        label_tok = next(
            (t for t in tokens if t.text.strip().lower() == label_text.lower()),
            None,
        )
        if label_tok is None:
            continue
        candidates = [
            t for t in tokens
            if _TIME_RE.match(t.text.strip())
            and t.y_centre > label_tok.y_centre
            and t.y_centre - label_tok.y_centre < 0.05
            and abs(t.x_centre - label_tok.x_centre) < 0.08
        ]
        if candidates:
            candidates.sort(key=lambda t: t.y_centre)
            m = _TIME_RE.match(candidates[0].text.strip())
            results[label_text.lower()] = int(m.group(1)) * 60 + int(m.group(2))

    if {"day", "night", "total"}.issubset(results):
        return results["day"], results["night"], results["total"]

    text = " ".join(t.text for t in tokens)
    fallback: dict[str, int] = {}
    for label, target in (("Day", "day"), ("Night", "night"), ("Total", "total")):
        m = re.search(rf"{label}\s+(\d{{1,2}}):(\d{{2}})", text, re.IGNORECASE)
        if m:
            fallback[target] = int(m.group(1)) * 60 + int(m.group(2))
    if {"day", "night", "total"}.issubset(fallback):
        return fallback["day"], fallback["night"], fallback["total"]

    # Defensive: if we know Day and Night but missed Total, infer it.
    # The pair.py sanity check tolerates +/- 1m so this is consistent.
    combined = {**fallback, **results}
    if {"day", "night"}.issubset(combined) and "total" not in combined:
        combined["total"] = combined["day"] + combined["night"]
        return combined["day"], combined["night"], combined["total"]

    partial = results or fallback
    raise ParseError(
        f"Could not parse Day/Night/Total summary. Partial: {partial}. "
        f"Try 'drivelog debug <screenshot>' to inspect OCR output."
    )


def parse_detail(tokens: list[OcrToken], image_path: Path | None = None) -> TripDetail:
    base_date = screenshot_date(image_path)
    header = parse_header_timestamp(tokens, base_date)
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
        start_time=_parse_datetime_from_text(rows["Start Time"], base_date),
        end_time=_parse_datetime_from_text(rows["End Time"], base_date),
        start_odometer=_parse_odometer(rows["Start Odometer"]),
        end_odometer=_parse_odometer(rows["End Odometer"]),
        day_minutes=day_min,
        night_minutes=night_min,
        total_minutes=total_min,
    )


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
    base_date = screenshot_date(image_path)
    header = parse_header_timestamp(tokens, base_date)

    if image_path is not None:
        from .iconselect import detect_multiple_selected, detect_selected
        weather_list = detect_multiple_selected(image_path, WEATHER_OPTIONS, tokens)
        weather = ", ".join(weather_list) if weather_list else "Unknown"
        road_list = detect_multiple_selected(image_path, ROAD_OPTIONS, tokens)
        road_type = ", ".join(road_list) if road_list else "Unknown"
        traffic_list = detect_multiple_selected(image_path, TRAFFIC_OPTIONS, tokens)
        traffic = ", ".join(traffic_list) if traffic_list else "Unknown"
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


_TAB_BAR_LABELS = {"trips", "learn", "logbook", "settings"}


def _extract_notes(tokens: list[OcrToken]) -> str:
    """Anything between the 'Notes' label and the iOS tab bar.

    The tab bar (Trips / Learn / Logbook / Settings) is the only thing
    that ever appears below Notes in this app. If we see one of those
    labels, use its Y as the cutoff; otherwise take everything below
    Notes. This is robust to screenshots that are cropped above the tab
    bar (where no cutoff is needed) and screenshots that include it.
    """
    notes_token = next((t for t in tokens if t.text.strip().lower() == "notes"), None)
    if notes_token is None:
        return ""

    tab_bar_ys = [
        t.y_centre for t in tokens
        if t.y_centre > notes_token.y_centre + 0.005
        and t.text.strip().lower() in _TAB_BAR_LABELS
    ]
    upper_bound = min(tab_bar_ys) if tab_bar_ys else 1.0

    below = [
        t for t in tokens
        if notes_token.y_centre + 0.005 < t.y_centre < upper_bound
        and t.text.strip().lower() not in _TAB_BAR_LABELS
    ]
    below.sort(key=lambda t: (round(t.y_centre, 3), t.x_centre))
    return " ".join(t.text for t in below).strip()
