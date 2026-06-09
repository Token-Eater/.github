"""Interactive review of pending trips before merging into trips.json."""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .config import Paths
from .model import Trip
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
        if trip.review_reasons:
            console.print("[yellow]Needs review:[/yellow]")
            for r in trip.review_reasons:
                console.print(f"  • {r}")
            trip = _fill_conditions(console, trip)

        choice = Prompt.ask(
            "Action (a=approve, s=skip, d=discard)",
            choices=["a", "s", "d"],
            default="a",
            show_choices=True,
        )
        if choice == "a":
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
    console.print(tbl)
    console.print(
        "[dim]Captured: road type / traffic / feel / notes are stored but not "
        "printed (ACT paper book has no columns for them).[/dim]"
    )
    console.print(
        "Actions: [bold]a[/bold]=approve into trips.json   "
        "[bold]s[/bold]=skip (leave in pending)   "
        "[bold]d[/bold]=discard",
        style="dim",
    )


def _fill_conditions(console: Console, trip: Trip) -> Trip:
    if trip.weather == "Unknown":
        trip.weather = Prompt.ask("Weather", choices=list(WEATHER_OPTIONS), default="Fine")
    if trip.road_type == "Unknown":
        trip.road_type = Prompt.ask("Road type", choices=list(ROAD_OPTIONS), default="Quiet Street")
    if trip.traffic == "Unknown":
        trip.traffic = Prompt.ask("Traffic", choices=list(TRAFFIC_OPTIONS), default="Light")
    if trip.feel == "Unknown":
        trip.feel = Prompt.ask("Feel", choices=list(FEEL_OPTIONS), default="Good")
    return trip
