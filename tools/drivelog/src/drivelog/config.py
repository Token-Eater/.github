from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .model import Supervisor

TZ = ZoneInfo("Australia/Sydney")  # ACT follows NSW DST


@dataclass
class Paths:
    root: Path
    intake: Path
    pending: Path
    archive: Path
    trips_json: Path
    supervisors_yaml: Path
    out: Path

    @classmethod
    def at(cls, root: Path) -> Paths:
        return cls(
            root=root,
            intake=root / "data" / "intake",
            pending=root / "data" / "pending",
            archive=root / "data" / "archive",
            trips_json=root / "data" / "trips.json",
            supervisors_yaml=root / "config" / "supervisors.yaml",
            out=root / "out",
        )


def project_root() -> Path:
    """Drivelog project root (where pyproject.toml lives)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate drivelog project root")


def load_supervisors(path: Path) -> list[Supervisor]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or []
    return [Supervisor(**entry) for entry in raw]


def resolve_supervisor(label: str, supervisors: list[Supervisor]) -> Supervisor | None:
    for s in supervisors:
        if s.matches(label):
            return s
    return None
