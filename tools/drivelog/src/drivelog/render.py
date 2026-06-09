"""Render Day / Night log book pages as PDF, matching the ACT layout."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .model import LogRow, TimeBand

# Approximated from the ACT log book scans.
DAY_COLOUR = colors.HexColor("#1F2E5A")  # deep navy header band
NIGHT_COLOUR = colors.HexColor("#F26522")  # bright orange header band

ROWS_PER_SECTION = 7  # matches the scans (~7 rows per half-page)
WEATHER_MAX_CHARS = 14  # approx fit in the 22mm WEATHER CONDITIONS column at 8pt


@dataclass
class _VisualRow:
    """One printed row: either a LogRow's primary view or a continuation of its weather."""
    log_row: LogRow
    weather: str
    is_continuation: bool = False


def _split_weather(weather: str) -> tuple[str, str]:
    """Split a comma-separated weather string at a comma so the first part fits the column."""
    if len(weather) <= WEATHER_MAX_CHARS:
        return weather, ""
    parts = [p.strip() for p in weather.split(",")]
    primary = ""
    i = 0
    for i, part in enumerate(parts):
        candidate = f"{primary}, {part}" if primary else part
        if len(candidate) > WEATHER_MAX_CHARS and primary:
            break
        primary = candidate
    else:
        i = len(parts)
    rest = ", ".join(parts[i:])
    return primary, rest


def _expand_for_weather(rows: list[LogRow]) -> list[_VisualRow]:
    out: list[_VisualRow] = []
    for r in rows:
        primary, cont = _split_weather(r.weather)
        out.append(_VisualRow(log_row=r, weather=primary))
        if cont:
            out.append(_VisualRow(log_row=r, weather=cont, is_continuation=True))
    return out


def _chunk_keep_pairs(rows: list[_VisualRow], size: int):
    section: list[_VisualRow] = []
    i = 0
    while i < len(rows):
        consume = 2 if i + 1 < len(rows) and rows[i + 1].is_continuation else 1
        if section and len(section) + consume > size:
            yield section
            section = []
        section.extend(rows[i:i + consume])
        i += consume
    if section:
        yield section

COLUMNS = (
    ("DATE", 18 * mm),
    ("WEATHER\nCONDITIONS", 22 * mm),
    ("SD NAME", 26 * mm),
    ("SD LICENCE", 22 * mm),
    ("SD SIGNATURE", 26 * mm),
    ("START\nTIME", 14 * mm),
    ("FINISH\nTIME", 14 * mm),
    ("ODOMETER\nSTART", 16 * mm),
    ("ODOMETER\nFINISH", 16 * mm),
    ("TOTAL\nTIME", 14 * mm),
)


def render_pages(
    rows: list[LogRow],
    band: TimeBand,
    output: Path,
    title_prefix: str = "RECORD OF DRIVING HOURS",
) -> Path:
    """Write a PDF of the given band's rows, paginating into half-page sections."""
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    band_colour = DAY_COLOUR if band == TimeBand.DAY else NIGHT_COLOUR
    band_label = "DAY" if band == TimeBand.DAY else "NIGHT"
    title_text = (
        f"{title_prefix} – {band_label}" if band == TimeBand.DAY
        else f"RECORD OF PRACTICE DRIVING HOURS – {band_label}"
    )

    rows_for_band = [r for r in rows if r.band == band]
    visual_rows = _expand_for_weather(rows_for_band)
    sections = list(_chunk_keep_pairs(visual_rows, ROWS_PER_SECTION))
    if not sections:
        sections = [[]]

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.textColor = band_colour
    subtitle_style = styles["Heading3"]
    subtitle_style.textColor = colors.grey

    story = []
    running_total = timedelta()
    for i, section in enumerate(sections):
        if i > 0:
            story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(title_text, title_style))
        story.append(Paragraph("WITH A SUPERVISING DRIVER", subtitle_style))
        story.append(Spacer(1, 2 * mm))
        section_total = sum(
            (vr.log_row.total for vr in section if not vr.is_continuation),
            timedelta(),
        )
        running_total += section_total
        story.append(_section_table(section, band_colour, section_total))

    doc.build(story)
    return output


def _section_table(rows: list[_VisualRow], band_colour, subtotal: timedelta) -> Table:
    headers = [h for h, _ in COLUMNS]
    col_widths = [w for _, w in COLUMNS]

    body_rows: list[list] = []
    for vr in rows:
        if vr.is_continuation:
            body_rows.append([
                "", f"↳ {vr.weather}", "", "", "", "", "", "", "", "",
            ])
            continue
        r = vr.log_row
        body_rows.append([
            r.date.strftime("%d/%m/%Y"),
            vr.weather,
            r.sd_name,
            r.sd_licence,
            _signature_cell(r.sd_signature_image),
            r.start_time.strftime("%H:%M"),
            r.finish_time.strftime("%H:%M"),
            f"{r.odometer_start:,}",
            f"{r.odometer_finish:,}",
            r.total_str(),
        ])
    # Pad empty rows so layout matches the book even when under-filled.
    blank = ["", "", "", "", "", "", "", "", "", ""]
    while len(body_rows) < ROWS_PER_SECTION:
        body_rows.append(blank.copy())

    subtotal_secs = int(subtotal.total_seconds())
    subtotal_str = f"{subtotal_secs // 3600:02d}:{(subtotal_secs % 3600) // 60:02d}"
    subtotal_row = ["SUBTOTAL OF HOURS", "", "", "", "", "", "", "", "", subtotal_str]

    data = [headers] + body_rows + [subtotal_row]
    tbl = Table(data, colWidths=col_widths, rowHeights=[12 * mm] + [10 * mm] * ROWS_PER_SECTION + [8 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), band_colour),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, 0), 3),
        ("RIGHTPADDING", (0, 0), (-1, 0), 3),

        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 8),
        ("VALIGN", (0, 1), (-1, -2), "MIDDLE"),
        ("GRID", (0, 1), (-1, -2), 0.25, colors.grey),

        ("BACKGROUND", (0, -1), (-1, -1), band_colour),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 8),
        ("ALIGN", (0, -1), (-2, -1), "RIGHT"),
        ("ALIGN", (-1, -1), (-1, -1), "RIGHT"),
        ("SPAN", (0, -1), (-2, -1)),
    ]))
    return tbl


def _signature_cell(path: str | None):
    if not path:
        return ""
    try:
        return Image(path, width=22 * mm, height=8 * mm)
    except Exception:
        return ""


