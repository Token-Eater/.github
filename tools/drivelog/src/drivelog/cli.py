"""Drivelog command-line entrypoint."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .classify import ScreenKind, classify
from .config import Paths, load_supervisors, project_root, resolve_supervisor
from .daynight import split_trip
from .model import TimeBand
from .pair import IngestedScreenshot, pair_and_merge
from .parse import ParseError, parse_conditions, parse_detail
from .render import render_pages
from .review import review_pending
from .store import (
    archive_screenshot,
    load_trips,
    save_pending,
    save_trips,
)

app = typer.Typer(help="iPhone screenshots → ACT learner log book pages.")
console = Console()


def _paths(root: Path | None) -> Paths:
    return Paths.at(root or project_root())


def _shots_for_trip(shots, header_ts):
    return [
        s for s in shots
        if (s.detail and s.detail.header_timestamp == header_ts)
        or (s.conditions and s.conditions.header_timestamp == header_ts)
    ]


@app.command()
def ingest(
    root: Path = typer.Option(None, "--root", help="Project root (defaults to package location)."),
) -> None:
    """OCR + classify + pair screenshots in data/intake, write to data/pending."""
    from .ocr import ocr_image  # lazy: only here do we need ocrmac.

    paths = _paths(root)
    paths.intake.mkdir(parents=True, exist_ok=True)
    images = sorted([
        p for p in paths.intake.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".heic"}
    ])
    if not images:
        console.print(f"[dim]No screenshots in {paths.intake}[/dim]")
        raise typer.Exit()

    supervisors = load_supervisors(paths.supervisors_yaml)
    shots: list[IngestedScreenshot] = []

    for img in images:
        tokens = ocr_image(img)
        kind = classify(tokens)
        try:
            if kind == ScreenKind.DETAIL:
                shots.append(IngestedScreenshot(path=img, kind=kind, detail=parse_detail(tokens)))
            elif kind == ScreenKind.CONDITIONS:
                shots.append(IngestedScreenshot(path=img, kind=kind, conditions=parse_conditions(tokens, image_path=img)))
            else:
                console.print(f"[yellow]Could not classify {img.name}[/yellow]")
                shots.append(IngestedScreenshot(path=img, kind=kind))
        except ParseError as e:
            console.print(f"[red]{img.name}: {e}[/red]")

    result = pair_and_merge(shots, supervisors)

    existing = load_trips(paths)
    new_count = 0
    for trip in result.trips:
        if trip.trip_id in existing:
            console.print(f"[dim]Skip duplicate {trip.trip_id} ({trip.header_timestamp:%Y-%m-%d %H:%M})[/dim]")
            continue
        save_pending(paths, trip)
        new_count += 1
        for shot in _shots_for_trip(shots, trip.header_timestamp):
            archive_screenshot(paths, shot.path, trip.header_timestamp)

    for shot in result.unpaired:
        console.print(f"[yellow]Unpaired: {shot.path.name} ({shot.kind.value})[/yellow]")
    for path, msg in result.errors:
        console.print(f"[red]{path.name}: {msg}[/red]")

    console.print(f"[green]Ingested {new_count} new trip(s) to {paths.pending}[/green]")


@app.command()
def review(
    root: Path = typer.Option(None, "--root"),
) -> None:
    """Review pending trips: approve, fill conditions, discard."""
    paths = _paths(root)
    approved = review_pending(paths)
    console.print(f"[green]Approved {approved} trip(s) into {paths.trips_json}[/green]")


@app.command()
def render(
    period: str = typer.Option(None, "--period", help="Filter to YYYY-MM (default: all)."),
    root: Path = typer.Option(None, "--root"),
) -> None:
    """Render Day and Night PDFs for approved trips."""
    paths = _paths(root)
    trips = load_trips(paths)
    if period:
        trips = {tid: t for tid, t in trips.items() if t.header_timestamp.strftime("%Y-%m") == period}
    if not trips:
        console.print("[yellow]No trips to render.[/yellow]")
        raise typer.Exit()

    supervisors = load_supervisors(paths.supervisors_yaml)
    rows = []
    for trip in sorted(trips.values(), key=lambda t: t.header_timestamp):
        sup = resolve_supervisor(trip.supervisor, supervisors)
        rows.extend(split_trip(trip, sup))

    tag = period or "all"
    out_day = paths.out / f"drivelog-{tag}-day.pdf"
    out_night = paths.out / f"drivelog-{tag}-night.pdf"

    day_rows = [r for r in rows if r.band == TimeBand.DAY]
    night_rows = [r for r in rows if r.band == TimeBand.NIGHT]
    if day_rows:
        render_pages(rows, TimeBand.DAY, out_day)
        console.print(f"[green]Wrote {out_day} ({len(day_rows)} rows)[/green]")
    if night_rows:
        render_pages(rows, TimeBand.NIGHT, out_night)
        console.print(f"[green]Wrote {out_night} ({len(night_rows)} rows)[/green]")
    if not day_rows and not night_rows:
        console.print("[yellow]No day or night rows to render.[/yellow]")


@app.command()
def debug(
    image: Path = typer.Argument(..., help="Path to a single screenshot to inspect."),
) -> None:
    """Print every OCR token from one screenshot with text, confidence, and position.

    Useful when parse fails: shows exactly what Vision saw so you can tell
    whether the issue is OCR quality or our spatial assumptions.
    """
    from .ocr import ocr_image

    tokens = ocr_image(image)
    kind = classify(tokens)
    console.print(f"[bold]Classified as:[/bold] {kind.value}  ({len(tokens)} tokens)")
    console.print(f"{'Text':<52} {'Conf':>5}  {'x':>5} {'y_top':>6} {'w':>5} {'h':>5}")
    for t in tokens:
        y_top = 1.0 - (t.y + t.h)
        console.print(
            f"{t.text[:50]:<52} {t.confidence:.2f}  "
            f"{t.x:.3f} {y_top:.3f} {t.w:.3f} {t.h:.3f}"
        )


@app.command()
def status(
    root: Path = typer.Option(None, "--root"),
) -> None:
    """Show pending vs canonical counts."""
    from .store import load_pending

    paths = _paths(root)
    pending = load_pending(paths)
    trips = load_trips(paths)
    intake = [
        p for p in (paths.intake.iterdir() if paths.intake.exists() else [])
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".heic"}
    ]
    console.print(f"intake screenshots : {len(intake)}")
    console.print(f"pending trips      : {len(pending)}")
    console.print(f"approved trips     : {len(trips)}")


if __name__ == "__main__":
    app()
