"""Interactive review of pending trips before merging into trips.json."""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .config import Paths, append_supervisor, load_supervisors, resolve_supervisor
from .model import Supervisor, Trip
from .parse import FEEL_OPTIONS, ROAD_OPTIONS, TRAFFIC_OPTIONS, WEATHER_OPTIONS
from .store import discard_pending, load_pending, load_trips, save_trips


def review_pending(paths: Paths) -> int:
    """Walk through pending trips with the user. Returns number approved."""
    console = Console()
    pending = load_pending(paths)
    if not pending:
        console.print("[green]No pending trips.[/green]")
        return 0

    canonical = load_trips(paths)
    approved = 0
    for trip in sorted(pending.values(), key=lambda t: t.header_timestamp):
        _show(console, trip)
        _maybe_register_supervisor(console, trip, paths)
        if trip.review_reasons:
            shown = [r for r in trip.review_reasons if "not in supervisors.yaml" not in r]
            if shown:
                console.print("[yellow]Needs review:[/yellow]")
                for r in shown:
                    console.print(f"  • {r}")
            trip = _fill_conditions(console, trip)

        console.print(
            "Actions: [bold]a[/bold]=approve   [bold]e[/bold]=edit conditions then approve   "
            "[bold]s[/bold]=skip (leave in pending)   [bold]d[/bold]=discard",
            style="dim",
        )
        choice = Prompt.ask(
            "Action (a=approve, e=edit conditions then approve, s=skip, d=discard)",
            choices=["a", "e", "s", "d"],
            default="a",
            show_choices=True,
        )
        if choice == "e":
            trip = _edit_conditions(console, trip)
            trip.needs_review = False
            trip.review_reasons = []
            canonical[trip.trip_id] = trip
            discard_pending(paths, trip.trip_id)
            approved += 1
        elif choice == "a":
            trip.needs_review = False
            trip.review_reasons = []
            canonical[trip.trip_id] = trip
            discard_pending(paths, trip.trip_id)
            approved += 1
        elif choice == "d":
            discard_pending(paths, trip.trip_id)
            console.print("[red]Discarded.[/red]")
        else:
            console.print("[yellow]Skipped (left in pending).[/yellow]")

    save_trips(paths, canonical)
    return approved


def _show(console: Console, trip: Trip) -> None:
    tbl = Table(title=f"Trip {trip.trip_id} – {trip.header_timestamp:%a %d %b %Y %H:%M}")
    tbl.add_column("Field")
    tbl.add_column("Value")
    tbl.add_row("Vehicle", trip.vehicle)
    tbl.add_row("Supervisor", trip.supervisor)
    tbl.add_row("Route", f"{trip.start_suburb} → {trip.end_suburb}")
    tbl.add_row(
        "Time",
        f"{trip.start_time:%H:%M} → {trip.end_time:%H:%M} "
        f"(day {trip.day_minutes}m + night {trip.night_minutes}m)",
    )
    tbl.add_row("Odometer", f"{trip.start_odometer:,} → {trip.end_odometer:,} ({trip.km()} km)")
    tbl.add_row("Conditions", f"weather={trip.weather} road={trip.road_type} traffic={trip.traffic} feel={trip.feel}")
    if trip.notes:
        tbl.add_row("Notes", trip.notes)
    if trip.source_files:
        tbl.add_row("Source", ", ".join(trip.source_files))
    console.print(tbl)
    console.print(
        "[dim]Captured: road type / traffic / feel / notes are stored but not "
        "printed (ACT paper book has no columns for them).[/dim]"
    )


def _fill_conditions(console: Console, trip: Trip) -> Trip:
    """Prompt only for fields the detector returned as Unknown."""
    if trip.weather == "Unknown":
        trip.weather = _prompt_multi(console, "Weather", WEATHER_OPTIONS, "", "Fine")
    if trip.road_type == "Unknown":
        trip.road_type = _prompt_multi(console, "Road types", ROAD_OPTIONS, "", "Quiet Street")
    if trip.traffic == "Unknown":
        trip.traffic = _prompt_multi(console, "Traffic", TRAFFIC_OPTIONS, "", "Light")
    if trip.feel == "Unknown":
        trip.feel = Prompt.ask("Feel", choices=list(FEEL_OPTIONS), default="Good")
    return trip


def _edit_conditions(console: Console, trip: Trip) -> Trip:
    """Prompt for every condition, defaulting to the currently-stored value."""
    def _default(value: str, options: tuple[str, ...], fallback: str) -> str:
        return value if value in options else fallback

    trip.weather = _prompt_multi(console, "Weather", WEATHER_OPTIONS, trip.weather, "Fine")
    trip.road_type = _prompt_multi(console, "Road types", ROAD_OPTIONS, trip.road_type, "Quiet Street")
    trip.traffic = _prompt_multi(console, "Traffic", TRAFFIC_OPTIONS, trip.traffic, "Light")
    trip.feel = Prompt.ask(
        "Feel", choices=list(FEEL_OPTIONS),
        default=_default(trip.feel, FEEL_OPTIONS, "Good"),
    )
    new_notes = Prompt.ask("Notes (Enter to keep current)", default=trip.notes)
    trip.notes = new_notes
    return trip


def _maybe_register_supervisor(console: Console, trip: Trip, paths: Paths) -> None:
    """If the trip's supervisor isn't in supervisors.yaml, offer to add them.

    The SD licence number isn't shown on the iPhone trip detail screen, so
    new supervisors need to be registered once. Append to supervisors.yaml
    here so the next ingest resolves the licence automatically.
    """
    supervisors = load_supervisors(paths.supervisors_yaml)
    if resolve_supervisor(trip.supervisor, supervisors):
        return
    console.print(
        f"[yellow]Supervisor '{trip.supervisor}' is new — register them so their "
        f"licence number prints in the SD LICENCE column.[/yellow]"
    )
    licence = Prompt.ask(
        f"Licence number for {trip.supervisor} (Enter to skip)",
        default="",
    )
    if not licence.strip():
        console.print("[dim]Skipped — SD LICENCE will print blank for this trip.[/dim]")
        return
    append_supervisor(
        paths.supervisors_yaml,
        Supervisor(
            full_name=trip.supervisor,
            licence_number=licence.strip(),
            aliases=[trip.supervisor],
        ),
    )
    console.print(f"[green]Added '{trip.supervisor}' to supervisors.yaml[/green]")


def _prompt_multi(console: Console, label: str, options: tuple[str, ...], current: str, fallback: str) -> str:
    """Multi-select prompt. Accepts comma-separated input; validates each value."""
    default = current if current and current != "Unknown" else fallback
    while True:
        raw = Prompt.ask(
            f"{label} (comma-separated; options: {' | '.join(options)})",
            default=default,
        )
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        invalid = [p for p in parts if p not in options]
        if invalid:
            console.print(f"[red]Not valid for {label}: {invalid}. Try again.[/red]")
            continue
        return ", ".join(parts) if parts else "Unknown"
