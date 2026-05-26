from __future__ import annotations

from datetime import datetime, timedelta

from drivelog.config import TZ
from drivelog.daynight import split_trip
from drivelog.model import Supervisor, TimeBand, Trip


def _trip(day=30, night=0):
    start = datetime(2026, 5, 2, 17, 0, tzinfo=TZ)
    return Trip(
        trip_id="abc",
        header_timestamp=start,
        vehicle="123ABC",
        supervisor="Oliver Mitchell",
        start_suburb="Barton",
        end_suburb="Capital Hill",
        start_time=start,
        end_time=start + timedelta(minutes=day + night),
        start_odometer=1000,
        end_odometer=1010,
        day_minutes=day,
        night_minutes=night,
        total_minutes=day + night,
        weather="Fine",
        road_type="Quiet Street",
        traffic="Light",
        feel="Good",
    )


def _sup():
    return Supervisor(full_name="Oliver Mitchell", licence_number="12345678", aliases=["O M"])


def test_day_only_emits_one_day_row():
    rows = split_trip(_trip(day=30, night=0), _sup())
    assert len(rows) == 1
    assert rows[0].band == TimeBand.DAY
    assert rows[0].sd_licence == "12345678"
    assert rows[0].total == timedelta(minutes=30)


def test_night_only_emits_one_night_row():
    rows = split_trip(_trip(day=0, night=20), _sup())
    assert len(rows) == 1
    assert rows[0].band == TimeBand.NIGHT


def test_mixed_emits_two_rows_sharing_trip_id():
    trip = _trip(day=15, night=10)
    rows = split_trip(trip, _sup())
    assert len(rows) == 2
    assert {r.band for r in rows} == {TimeBand.DAY, TimeBand.NIGHT}
    assert {r.trip_id for r in rows} == {"abc"}
    day_row = next(r for r in rows if r.band == TimeBand.DAY)
    night_row = next(r for r in rows if r.band == TimeBand.NIGHT)
    assert day_row.total == timedelta(minutes=15)
    assert night_row.total == timedelta(minutes=10)
    # Boundary: day finishes where night starts.
    assert day_row.finish_time == night_row.start_time
    # Whole-trip odometer kept on each row (legal supplementary-sheet convention).
    assert day_row.odometer_start == night_row.odometer_start == 1000
    assert day_row.odometer_finish == night_row.odometer_finish == 1010
