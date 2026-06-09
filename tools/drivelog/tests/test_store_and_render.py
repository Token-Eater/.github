from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from drivelog.config import TZ, Paths
from drivelog.model import LogRow, TimeBand, Trip
from drivelog.render import render_pages
from drivelog.store import load_trips, save_pending, save_trips


def _trip(tid="abc"):
    ts = datetime(2026, 5, 2, 9, 31, tzinfo=TZ)
    return Trip(
        trip_id=tid,
        header_timestamp=ts,
        vehicle="123ABC",
        supervisor="Oliver Mitchell",
        start_suburb="Barton",
        end_suburb="Capital Hill",
        start_time=ts,
        end_time=ts + timedelta(minutes=1),
        start_odometer=1000,
        end_odometer=1002,
        day_minutes=1,
        night_minutes=0,
        total_minutes=1,
        weather="Fine",
        road_type="Quiet Street",
        traffic="Moderate",
        feel="Meh",
    )


def _paths(tmp: Path) -> Paths:
    return Paths(
        root=tmp,
        intake=tmp / "intake",
        pending=tmp / "pending",
        archive=tmp / "archive",
        trips_json=tmp / "trips.json",
        supervisors_yaml=tmp / "supervisors.yaml",
        out=tmp / "out",
    )


def test_roundtrip_trip_json(tmp_path):
    paths = _paths(tmp_path)
    save_trips(paths, {"abc": _trip()})
    loaded = load_trips(paths)
    assert "abc" in loaded
    assert loaded["abc"].vehicle == "123ABC"
    assert loaded["abc"].start_time.tzinfo is not None


def test_save_pending_creates_file(tmp_path):
    paths = _paths(tmp_path)
    save_pending(paths, _trip("xyz"))
    assert (paths.pending / "xyz.json").exists()


def test_render_day_pdf_produces_file(tmp_path):
    paths = _paths(tmp_path)
    trip = _trip()
    rows = [LogRow(
        trip_id=trip.trip_id,
        band=TimeBand.DAY,
        date=trip.header_timestamp,
        weather=trip.weather,
        sd_name="Oliver Mitchell",
        sd_licence="12345678",
        sd_signature_image=None,
        start_time=trip.start_time,
        finish_time=trip.end_time,
        odometer_start=trip.start_odometer,
        odometer_finish=trip.end_odometer,
        total=timedelta(minutes=1),
    )]
    out = paths.out / "drivelog-day.pdf"
    render_pages(rows, TimeBand.DAY, out)
    assert out.exists() and out.stat().st_size > 0


def test_render_handles_empty_rows(tmp_path):
    paths = _paths(tmp_path)
    out = paths.out / "drivelog-night.pdf"
    render_pages([], TimeBand.NIGHT, out)
    assert out.exists() and out.stat().st_size > 0


def test_split_weather_short_string_unchanged():
    from drivelog.render import _split_weather
    primary, cont = _split_weather("Fine")
    assert primary == "Fine"
    assert cont == ""


def test_split_weather_overflow_breaks_at_comma():
    from drivelog.render import _split_weather, WEATHER_MAX_CHARS
    primary, cont = _split_weather("Fine, Rain, Snow, Icy, Fog")
    assert len(primary) <= WEATHER_MAX_CHARS
    assert cont != ""
    # Original is preserved if we rejoin
    assert {p.strip() for p in (primary + ", " + cont).split(",")} == {"Fine", "Rain", "Snow", "Icy", "Fog"}


def test_expand_for_weather_emits_continuation_row():
    from drivelog.render import _expand_for_weather
    from datetime import datetime, timedelta
    from drivelog.config import TZ
    long_row = LogRow(
        trip_id="x", band=TimeBand.DAY,
        date=datetime(2026, 6, 6, 9, tzinfo=TZ),
        weather="Fine, Rain, Snow, Icy, Fog",
        sd_name="Test", sd_licence="123", sd_signature_image=None,
        start_time=datetime(2026, 6, 6, 9, tzinfo=TZ),
        finish_time=datetime(2026, 6, 6, 10, tzinfo=TZ),
        odometer_start=1000, odometer_finish=1010,
        total=timedelta(hours=1),
    )
    visuals = _expand_for_weather([long_row])
    assert len(visuals) == 2
    assert not visuals[0].is_continuation
    assert visuals[1].is_continuation


def test_chunk_keep_pairs_doesnt_split_continuation_across_sections():
    from drivelog.render import _chunk_keep_pairs, _VisualRow
    # 5 normal rows + 1 primary + 1 continuation = 7 visual rows, ROWS_PER_SECTION=7
    # but if we ask for section size 6 the pair must move to the next section.
    rows = [_VisualRow(log_row=None, weather=f"r{i}") for i in range(5)]
    rows.append(_VisualRow(log_row=None, weather="primary"))
    rows.append(_VisualRow(log_row=None, weather="cont", is_continuation=True))
    sections = list(_chunk_keep_pairs(rows, 6))
    assert len(sections) == 2
    assert len(sections[0]) == 5
    assert len(sections[1]) == 2  # primary + continuation together
