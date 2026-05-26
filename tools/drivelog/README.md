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

# 3. Review pending trips (fill conditions, approve / discard)
drivelog review

# 4. Render printable PDFs
drivelog render --period 2026-05
open out/drivelog-2026-05-day.pdf

# Anytime: see what's pending
drivelog status
```

## What goes on each screenshot

- **Detail screen**: must show date header, Day/Night/Total summary, Vehicle, Supervisor, Start/End Suburb, Start/End Time, Start/End Odometer, and the "Signed off by …" line.
- **Conditions screen**: the weather/road/traffic/feel selectors and Notes. The selected option is detected during the review step (OCR can't read icon highlight state).

## Mixed day/night trips

If a trip straddles dusk and the app reports both Day and Night minutes, drivelog emits two rows — one on the Day page, one on the Night page — sharing a `trip_id` so the audit trail is clear.

## Data files

- `data/intake/` — drop screenshots here (gitignored).
- `data/pending/<trip_id>.json` — extracted but not yet approved (gitignored).
- `data/trips.json` — canonical, committed.
- `data/archive/YYYY-MM/` — original screenshots after ingest (gitignored).
- `out/` — rendered PDFs (gitignored).
