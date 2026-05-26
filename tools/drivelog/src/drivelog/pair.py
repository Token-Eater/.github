"""Pair classified detail/conditions screenshots and merge them into Trips."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .classify import ScreenKind
from .config import resolve_supervisor
from .model import Supervisor, Trip, TripConditions, TripDetail


@dataclass
class IngestedScreenshot:
    path: Path
    kind: ScreenKind
    detail: TripDetail | None = None
    conditions: TripConditions | None = None


@dataclass
class PairingResult:
    trips: list[Trip]
    unpaired: list[IngestedScreenshot]
    errors: list[tuple[Path, str]]


def trip_id(timestamp_iso: str, start_odo: int) -> str:
    """Stable id keyed on (header timestamp, start odometer) per dedupe rule."""
    raw = f"{timestamp_iso}|{start_odo}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def pair_and_merge(
    shots: list[IngestedScreenshot],
    supervisors: list[Supervisor],
) -> PairingResult:
    details = {s.detail.header_timestamp: s for s in shots if s.detail}
    conditions = {s.conditions.header_timestamp: s for s in shots if s.conditions}

    trips: list[Trip] = []
    errors: list[tuple[Path, str]] = []
    used: set[Path] = set()

    for ts, det_shot in details.items():
        det = det_shot.detail
        assert det is not None
        cond_shot = conditions.get(ts)
        if cond_shot is None:
            continue  # unpaired - handled below
        cond = cond_shot.conditions
        assert cond is not None

        # Day + Night must equal Total.
        if det.day_minutes + det.night_minutes != det.total_minutes:
            errors.append(
                (
                    det_shot.path,
                    f"Day ({det.day_minutes}m) + Night ({det.night_minutes}m) "
                    f"!= Total ({det.total_minutes}m)",
                )
            )

        # Sign-off / supervisor mismatch.
        if det.signed_off_by and det.signed_off_by.strip() != det.supervisor_label.strip():
            errors.append(
                (
                    det_shot.path,
                    f"Signed off by '{det.signed_off_by}' but supervisor field is "
                    f"'{det.supervisor_label}'",
                )
            )

        supervisor = resolve_supervisor(det.supervisor_label, supervisors)
        review_reasons: list[str] = []
        if supervisor is None:
            review_reasons.append(
                f"Supervisor '{det.supervisor_label}' not in supervisors.yaml"
            )
        # Conditions are always Unknown until the user picks them in review.
        if cond.weather == "Unknown":
            review_reasons.append("Conditions not yet set (weather/road/traffic/feel)")

        tid = trip_id(det.header_timestamp.isoformat(), det.start_odometer)
        trips.append(
            Trip(
                trip_id=tid,
                header_timestamp=det.header_timestamp,
                vehicle=det.vehicle,
                supervisor=supervisor.full_name if supervisor else det.supervisor_label,
                start_suburb=det.start_suburb,
                end_suburb=det.end_suburb,
                start_time=det.start_time,
                end_time=det.end_time,
                start_odometer=det.start_odometer,
                end_odometer=det.end_odometer,
                day_minutes=det.day_minutes,
                night_minutes=det.night_minutes,
                total_minutes=det.total_minutes,
                weather=cond.weather,
                road_type=cond.road_type,
                traffic=cond.traffic,
                feel=cond.feel,
                notes=cond.notes,
                needs_review=bool(review_reasons),
                review_reasons=review_reasons,
            )
        )
        used.add(det_shot.path)
        used.add(cond_shot.path)

    unpaired = [s for s in shots if s.path not in used]
    return PairingResult(trips=trips, unpaired=unpaired, errors=errors)
