"""Split a Trip into LogRows for the Day and/or Night log book pages."""

from __future__ import annotations

from datetime import timedelta

from .model import LogRow, Supervisor, TimeBand, Trip


def split_trip(trip: Trip, supervisor: Supervisor | None) -> list[LogRow]:
    """Return one or two LogRows depending on day/night composition.

    - Day only  -> 1 day row
    - Night only -> 1 night row
    - Mixed -> 2 rows sharing trip_id. Each row carries the full odometer
      range; total time is the band's portion. The split moment uses the
      app's reported boundary: day finishes at (start_time + day_minutes),
      night starts there.
    """
    sd_name = supervisor.full_name if supervisor else trip.supervisor
    sd_licence = supervisor.licence_number if supervisor else ""
    sd_signature = supervisor.signature_image if supervisor else None

    day_td = timedelta(minutes=trip.day_minutes)
    night_td = timedelta(minutes=trip.night_minutes)

    if trip.day_minutes > 0 and trip.night_minutes == 0:
        return [
            _row(trip, TimeBand.DAY, trip.start_time, trip.end_time, day_td,
                 trip.start_odometer, trip.end_odometer,
                 sd_name, sd_licence, sd_signature)
        ]
    if trip.night_minutes > 0 and trip.day_minutes == 0:
        return [
            _row(trip, TimeBand.NIGHT, trip.start_time, trip.end_time, night_td,
                 trip.start_odometer, trip.end_odometer,
                 sd_name, sd_licence, sd_signature)
        ]

    # Mixed: split time at the app's day/night boundary, split km proportionally
    # to time so the two rows together sum to the full trip km (no over-counting
    # if anyone tallies the page).
    boundary = trip.start_time + day_td
    total_km = trip.end_odometer - trip.start_odometer
    if trip.total_minutes > 0:
        day_km = round(total_km * trip.day_minutes / trip.total_minutes)
    else:
        day_km = total_km // 2
    day_odo_finish = trip.start_odometer + day_km
    return [
        _row(trip, TimeBand.DAY, trip.start_time, boundary, day_td,
             trip.start_odometer, day_odo_finish,
             sd_name, sd_licence, sd_signature),
        _row(trip, TimeBand.NIGHT, boundary, trip.end_time, night_td,
             day_odo_finish, trip.end_odometer,
             sd_name, sd_licence, sd_signature),
    ]


def _row(trip, band, start, finish, total, odo_start, odo_finish,
         sd_name, sd_licence, sd_signature):
    return LogRow(
        trip_id=trip.trip_id,
        band=band,
        date=trip.header_timestamp,
        weather=trip.weather,
        sd_name=sd_name,
        sd_licence=sd_licence,
        sd_signature_image=sd_signature,
        start_time=start,
        finish_time=finish,
        odometer_start=odo_start,
        odometer_finish=odo_finish,
        total=total,
    )
