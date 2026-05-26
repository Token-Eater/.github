"""Parse tests use synthetic OcrToken fixtures so we don't depend on ocrmac."""

from __future__ import annotations

from drivelog.ocr import OcrToken
from drivelog.parse import (
    ParseError,
    parse_conditions,
    parse_detail,
    parse_header_timestamp,
)


def _tokens(rows: list[tuple[float, list[str]]]) -> list[OcrToken]:
    """Build tokens from (y, [words]) rows. y is row index from top."""
    out: list[OcrToken] = []
    total_rows = max(y for y, _ in rows) + 1
    for y, words in rows:
        for x, word in enumerate(words):
            # ocrmac coords: origin bottom-left, so y=0 (top) -> bbox y near 1.0.
            bbox_y = 1.0 - ((y + 0.5) / total_rows) - 0.02
            out.append(
                OcrToken(
                    text=word,
                    confidence=0.99,
                    x=0.05 + x * 0.12,
                    y=bbox_y,
                    w=0.10,
                    h=0.02,
                )
            )
    return out


SAMPLE_DETAIL = _tokens([
    (0, ["2 May 2026 at 9:31 am"]),
    (1, ["Km", "2", "Day", "00:01", "+", "Night", "00:00", "=", "Total", "00:01"]),
    (2, ["Signed off by O M", "2 May 2026 at 9:34 am"]),
    (3, ["Vehicle", "123ABC"]),
    (4, ["Supervisor", "O M"]),
    (5, ["Start Suburb", "Barton, ACT"]),
    (6, ["End Suburb", "Capital Hill, ACT"]),
    (7, ["Start Time", "2 May 2026 at 9:31 am"]),
    (8, ["End Time", "2 May 2026 at 9:32 am"]),
    (9, ["Start Odometer", "1,000"]),
    (10, ["End Odometer", "1,002"]),
])


SAMPLE_CONDITIONS = _tokens([
    (0, ["2 May 2026 at 9:31 am"]),
    (1, ["What was the weather like?"]),
    (2, ["Fine", "Rain", "Snow", "Icy", "Fog"]),
    (3, ["What kind of roads did you drive on?"]),
    (4, ["Sealed", "Unsealed", "Quiet Street", "Main Road", "Multi-laned"]),
    (5, ["What was the traffic like?"]),
    (6, ["Light", "Moderate", "Heavy"]),
    (7, ["How did the practice feel?"]),
    (8, ["Awful", "Bad", "Meh", "Good", "Great"]),
    (9, ["Notes"]),
])


def test_header_timestamp_parses():
    ts = parse_header_timestamp(SAMPLE_DETAIL)
    assert ts.year == 2026 and ts.month == 5 and ts.day == 2
    assert ts.hour == 9 and ts.minute == 31


def test_parse_detail_extracts_all_fields():
    det = parse_detail(SAMPLE_DETAIL)
    assert det.vehicle == "123ABC"
    assert det.supervisor_label == "O M"
    assert det.signed_off_by == "O M"
    assert det.start_suburb == "Barton, ACT"
    assert det.end_suburb == "Capital Hill, ACT"
    assert det.start_odometer == 1000
    assert det.end_odometer == 1002
    assert det.day_minutes == 1
    assert det.night_minutes == 0
    assert det.total_minutes == 1


def test_parse_detail_raises_on_missing_fields():
    incomplete = _tokens([
        (0, ["2 May 2026 at 9:31 am"]),
        (1, ["Day", "00:01", "Night", "00:00", "Total", "00:01"]),
        (2, ["Vehicle", "123ABC"]),
    ])
    try:
        parse_detail(incomplete)
    except ParseError as e:
        assert "Missing fields" in str(e)
    else:
        raise AssertionError("expected ParseError")


def test_parse_conditions_leaves_selection_unknown():
    cond = parse_conditions(SAMPLE_CONDITIONS)
    assert cond.weather == "Unknown"
    assert cond.road_type == "Unknown"
    assert cond.traffic == "Unknown"
    assert cond.feel == "Unknown"
