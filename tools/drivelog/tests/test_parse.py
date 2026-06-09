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


def test_header_timestamp_parses_short_month_no_at_no_space():
    """Vision sometimes drops 'at' and the space before PM; some locales use 'Jun' not 'June'."""
    tokens = _tokens([(0, ["6 Jun 2026 2:42PM"])])
    ts = parse_header_timestamp(tokens)
    assert ts.year == 2026 and ts.month == 6 and ts.day == 6
    assert ts.hour == 14 and ts.minute == 42


def test_header_timestamp_parses_full_month_with_at():
    tokens = _tokens([(0, ["6 June 2026 at 2:42 PM"])])
    ts = parse_header_timestamp(tokens)
    assert ts.hour == 14 and ts.minute == 42


def test_header_timestamp_today_uses_base_date():
    from datetime import date
    tokens = _tokens([(0, ["Today at 3:34 am"])])
    ts = parse_header_timestamp(tokens, base_date=date(2026, 6, 8))
    assert ts.year == 2026 and ts.month == 6 and ts.day == 8
    assert ts.hour == 3 and ts.minute == 34


def test_header_timestamp_yesterday_subtracts_one_day():
    from datetime import date
    tokens = _tokens([(0, ["Yesterday at 11:59 pm"])])
    ts = parse_header_timestamp(tokens, base_date=date(2026, 6, 8))
    assert ts.year == 2026 and ts.month == 6 and ts.day == 7
    assert ts.hour == 23 and ts.minute == 59


def test_header_timestamp_ignores_ios_status_bar_clock():
    """'3:42' alone isn't a header timestamp - status-bar clock shouldn't false-match."""
    tokens = _tokens([
        (0, ["3:42", "91%"]),
        (1, ["Today at 3:34 am"]),
    ])
    from datetime import date
    ts = parse_header_timestamp(tokens, base_date=date(2026, 6, 8))
    assert ts.hour == 3 and ts.minute == 34  # matched 'Today at 3:34', not '3:42'


def test_extract_day_night_infers_total_from_day_plus_night():
    """If Day and Night parse but Total doesn't, fall back to day+night."""
    from drivelog.parse import _extract_day_night
    from drivelog.ocr import OcrToken
    pad = [(r, ["."]) for r in range(2, 20)]
    tokens = _tokens([
        (0, ["2 May 2026 at 9:31 am"]),
        (1, ["Km", "Day", "Night"]),
    ] + pad)
    tokens = [t for t in tokens if t.text != "."]
    label_y_centre = next(t for t in tokens if t.text == "Day").y_centre
    for text, x in [("00:04", 0.17), ("00:00", 0.29)]:
        tokens.append(OcrToken(
            text=text, confidence=0.99,
            x=x, y=(1 - label_y_centre) - 0.03 - 0.02, w=0.10, h=0.02,
        ))
    assert _extract_day_night(tokens) == (4, 0, 4)


def test_extract_day_night_handles_labels_above_values():
    """Real screenshots put Day/Night/Total labels on one row, values on the next."""
    from drivelog.parse import _extract_day_night

    # Pad with empty rows so the label-to-value gap is realistically small (<5% of image).
    pad = [(r, ["."]) for r in range(2, 20)]
    tokens = _tokens([
        (0, ["2 May 2026 at 9:31 am"]),
        (1, ["Km", "Day", "Night", "Total"]),
        # Values are on the row just after the labels: close in Y.
    ] + pad)
    # Replace one padding row with the actual values (close to the label row).
    tokens = [t for t in tokens if t.text != "."]
    # Add value tokens close to the label row's Y.
    label_y_centre = next(t for t in tokens if t.text == "Day").y_centre
    from drivelog.ocr import OcrToken
    for i, (text, x) in enumerate([("2", 0.05), ("00:01", 0.17), ("00:00", 0.29), ("00:01", 0.41)]):
        tokens.append(OcrToken(
            text=text, confidence=0.99,
            x=x, y=(1 - label_y_centre) - 0.03 - 0.02, w=0.10, h=0.02,
        ))
    assert _extract_day_night(tokens) == (1, 0, 1)


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


def test_extract_rows_strips_trailing_chevrons():
    """iOS tappable rows often pick up a chevron ('>', '›') after the value."""
    from drivelog.parse import _extract_rows
    tokens = _tokens([
        (0, ["Vehicle", "123ABC >"]),
        (1, ["Supervisor", "OM >"]),
        (2, ["Start Suburb", "Hackett, ACT ›"]),
        (3, ["End Suburb", "Red Hill, ACT ›"]),
        (4, ["Start Time", "6 Jun 2026 at 2:42 pm"]),
        (5, ["End Time", "6 Jun 2026 at 3:53 pm"]),
        (6, ["Start Odometer", "263,747"]),
        (7, ["End Odometer", "263,793"]),
    ])
    rows = _extract_rows(tokens)
    assert rows["Vehicle"] == "123ABC"
    assert rows["Supervisor"] == "OM"
    assert rows["Start Suburb"] == "Hackett, ACT"
    assert rows["End Suburb"] == "Red Hill, ACT"


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


def test_parse_conditions_without_image_leaves_selection_unknown():
    cond = parse_conditions(SAMPLE_CONDITIONS)
    assert cond.weather == "Unknown"
    assert cond.road_type == "Unknown"
    assert cond.traffic == "Unknown"
    assert cond.feel == "Unknown"


def test_extract_notes_below_label():
    from drivelog.parse import _extract_notes
    tokens = _tokens([
        (0, ["2 May 2026 at 9:31 am"]),
        (1, ["How did the practice feel?"]),
        (2, ["Awful", "Bad", "Meh", "Good", "Great"]),
        (3, ["Notes"]),
        (4, ["Roundabout", "felt", "tight"]),
        (5, ["good", "stop", "at", "lights"]),
    ])
    assert _extract_notes(tokens) == "Roundabout felt tight good stop at lights"


def test_extract_notes_empty_when_no_label():
    from drivelog.parse import _extract_notes
    assert _extract_notes(_tokens([(0, ["2 May 2026 at 9:31 am"])])) == ""


def test_extract_notes_stops_at_tab_bar():
    """If 'Trips/Learn/Logbook/Settings' tokens appear below Notes, stop there."""
    from drivelog.parse import _extract_notes
    tokens = _tokens([
        (0, ["Notes"]),
        (1, ["real", "notes", "content", "here"]),
        (2, ["Trips", "Learn", "Logbook", "Settings"]),
    ])
    assert _extract_notes(tokens) == "real notes content here"


def test_extract_notes_no_tab_bar_takes_everything():
    """Cropped screenshots without a tab bar should still capture notes."""
    from drivelog.parse import _extract_notes
    tokens = _tokens([
        (0, ["Notes"]),
        (1, ["only", "notes", "no", "tab", "bar"]),
    ])
    assert _extract_notes(tokens) == "only notes no tab bar"
