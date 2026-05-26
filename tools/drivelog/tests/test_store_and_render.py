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
