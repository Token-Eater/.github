# drivelog

Turn iPhone learner-driver app screenshots into printable ACT log book pages.

## Why

The ACT learner log book is still paper (blue Day pages, orange Night pages). The iPhone app records each trip well but has no export. So:

1. AirDrop two screenshots per trip from the iPhone to your Mac.
2. `drivelog ingest` OCRs them, pairs detail + conditions, and writes a pending trip.
3. `drivelog review` lets you fill in the conditions (weather/road/traffic/feel — the app shows these as coloured icons that OCR can't read) and approve.
4. `drivelog render` produces an A4 PDF that matches the ACT log book layout. Print it, slip it into the book, hand-sign the supervisor signature column.

Runs on macOS only (uses Apple's Vision framework via `ocrmac`).

## Install

```sh
cd tools/drivelog
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[mac]'
```

## Configure supervisors

`config/supervisors.yaml` maps the short label the app shows (e.g. `"O M"`) to the full name and licence number that go in the log book columns.

## Workflow

```sh
# 1. AirDrop screenshots from iPhone → tools/drivelog/data/intake/
# 2. OCR + classify + pair
drivelog ingest

# 3. Review pending trips (a=approve as-detected,
#    e=edit conditions then approve, s=skip, d=discard)
drivelog review

# 4. Render printable PDFs
drivelog render --period 2026-05
open out/drivelog-2026-05-day.pdf

# Anytime: see what's pending
drivelog status

# If something parses oddly, inspect raw OCR for one screenshot:
drivelog debug data/intake/IMG_1234.PNG
```

## What goes on each screenshot

- **Detail screen**: must show date header, Day/Night/Total summary, Vehicle, Supervisor, Start/End Suburb, Start/End Time, Start/End Odometer, and the "Signed off by …" line.
- **Conditions screen**: the weather / road / traffic / feel selectors and Notes. Selection is auto-detected by sampling pixels above each option label (lit icons are light blue vs dark grey for unselected). If the result is ambiguous you'll be asked to confirm during `review`.

## What's stored vs printed

Drivelog captures all of `weather`, `road_type`, `traffic`, `feel`, and `notes` into `trips.json` and shows them in `review`. Only `weather` is printed into the WEATHER CONDITIONS column of the ACT paper book (which has no columns for the rest). The extra fields are kept against the chance that ACT moves to a digital log book — they'll already be in your data.

`road_type` is multi-select (the app lets you tick more than one road type per trip), so it's stored as a comma-separated string like `"Quiet Street, Main Road, Multi-laned"`. The other three rows are single-select.

## When detection is wrong

Icon-state detection is heuristic (pixel sampling above each label, scoring by "blueness" of the circle background). If it ever picks something incorrect, hit `e` at the review prompt and walk through all five fields with the detected value as default — Enter to accept, type a new value to override.

## Mixed day/night trips

If a trip straddles dusk and the app reports both Day and Night minutes, drivelog emits two rows — one on the Day page, one on the Night page — sharing a `trip_id` so the audit trail is clear.

## Data files

- `data/intake/` — drop screenshots here (gitignored).
- `data/pending/<trip_id>.json` — extracted but not yet approved (gitignored).
- `data/trips.json` — canonical, committed.
- `data/archive/YYYY-MM/` — original screenshots after ingest (gitignored).
- `out/` — rendered PDFs (gitignored).
