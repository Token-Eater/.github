from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class TimeBand(str, Enum):
    DAY = "day"
    NIGHT = "night"


def _norm_name(s: str) -> str:
    """Collapse all whitespace and lowercase, so 'O M' and 'OM' compare equal."""
    return "".join(s.split()).lower()


@dataclass
class Supervisor:
    full_name: str
    licence_number: str
    aliases: list[str] = field(default_factory=list)
    signature_image: str | None = None

    def matches(self, app_label: str) -> bool:
        target = _norm_name(app_label)
        if target == _norm_name(self.full_name):
            return True
        return any(target == _norm_name(a) for a in self.aliases)


@dataclass
class TripDetail:
    """Fields parsed from the trip-detail screenshot (screenshot A)."""

    header_timestamp: datetime
    vehicle: str
    supervisor_label: str
    signed_off_by: str | None
    start_suburb: str
    end_suburb: str
    start_time: datetime
    end_time: datetime
    start_odometer: int
    end_odometer: int
    day_minutes: int
    night_minutes: int
    total_minutes: int


@dataclass
class TripConditions:
    """Fields parsed from the conditions screenshot (screenshot B)."""

    header_timestamp: datetime
    weather: str
    road_type: str
    traffic: str
    feel: str
    notes: str = ""


@dataclass
class Trip:
    """A canonical merged trip from a paired (detail, conditions) screenshot set."""

    trip_id: str
    header_timestamp: datetime
    vehicle: str
    supervisor: str
    start_suburb: str
    end_suburb: str
    start_time: datetime
    end_time: datetime
    start_odometer: int
    end_odometer: int
    day_minutes: int
    night_minutes: int
    total_minutes: int
    weather: str
    road_type: str
    traffic: str
    feel: str
    notes: str = ""
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    def km(self) -> int:
        return self.end_odometer - self.start_odometer

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("header_timestamp", "start_time", "end_time"):
            d[k] = getattr(self, k).isoformat()
        return d

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Trip:
        for k in ("header_timestamp", "start_time", "end_time"):
            data[k] = datetime.fromisoformat(data[k])
        return cls(**data)


@dataclass
class LogRow:
    """A single row on a printed log book page (already day/night split)."""

    trip_id: str
    band: TimeBand
    date: datetime
    weather: str
    sd_name: str
    sd_licence: str
    sd_signature_image: str | None
    start_time: datetime
    finish_time: datetime
    odometer_start: int
    odometer_finish: int
    total: timedelta

    def total_str(self) -> str:
        secs = int(self.total.total_seconds())
        return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}"
