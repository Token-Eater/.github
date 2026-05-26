"""Persistence: trips.json (canonical) and pending/*.json (awaiting review)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from .config import Paths
from .model import Trip


def load_trips(paths: Paths) -> dict[str, Trip]:
    if not paths.trips_json.exists():
        return {}
    raw = json.loads(paths.trips_json.read_text())
    return {entry["trip_id"]: Trip.from_json(entry) for entry in raw}


def save_trips(paths: Paths, trips: dict[str, Trip]) -> None:
    ordered = sorted(trips.values(), key=lambda t: t.header_timestamp)
    _atomic_write(paths.trips_json, json.dumps([t.to_json() for t in ordered], indent=2))


def load_pending(paths: Paths) -> dict[str, Trip]:
    pending: dict[str, Trip] = {}
    if not paths.pending.exists():
        return pending
    for f in sorted(paths.pending.glob("*.json")):
        data = json.loads(f.read_text())
        trip = Trip.from_json(data)
        pending[trip.trip_id] = trip
    return pending


def save_pending(paths: Paths, trip: Trip) -> Path:
    paths.pending.mkdir(parents=True, exist_ok=True)
    target = paths.pending / f"{trip.trip_id}.json"
    _atomic_write(target, json.dumps(trip.to_json(), indent=2))
    return target


def discard_pending(paths: Paths, trip_id: str) -> None:
    target = paths.pending / f"{trip_id}.json"
    if target.exists():
        target.unlink()


def archive_screenshot(paths: Paths, source: Path, when: datetime) -> Path:
    month_dir = paths.archive / when.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)
    target = month_dir / source.name
    if not target.exists():
        shutil.move(str(source), str(target))
    return target


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, target)
