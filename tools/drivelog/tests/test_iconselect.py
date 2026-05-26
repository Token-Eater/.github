"""Test icon-selection pixel sampling against a synthesized conditions image."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from drivelog.iconselect import detect_selected
from drivelog.ocr import OcrToken


IMG_W = 800
IMG_H = 1400

OPTIONS = ("Fine", "Rain", "Snow", "Icy", "Fog")

# Icon row centred near the top third of the image; labels just below.
ICON_Y_PX = 400
LABEL_Y_PX = 500


def _slot_x(i: int) -> int:
    return int((i + 0.5) * IMG_W / len(OPTIONS))


def _make_image(selected_index: int, path: Path) -> None:
    img = Image.new("RGB", (IMG_W, IMG_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, _ in enumerate(OPTIONS):
        cx = _slot_x(i)
        colour = (130, 175, 230) if i == selected_index else (50, 50, 55)
        draw.ellipse((cx - 50, ICON_Y_PX - 50, cx + 50, ICON_Y_PX + 50), fill=colour)
    img.save(path)


def _tokens_for_labels() -> list[OcrToken]:
    """OcrToken bbox for each label sitting just below its icon."""
    label_h_norm = 24 / IMG_H
    label_y_top_norm = LABEL_Y_PX / IMG_H
    # ocrmac y is bottom-left origin: y_bottom = 1 - (top + height)
    bbox_y = 1.0 - (label_y_top_norm + label_h_norm)

    out: list[OcrToken] = []
    for i, label in enumerate(OPTIONS):
        cx_norm = _slot_x(i) / IMG_W
        out.append(OcrToken(
            text=label,
            confidence=0.99,
            x=cx_norm - 0.05,
            y=bbox_y,
            w=0.10,
            h=label_h_norm,
        ))
    return out


@pytest.mark.parametrize("selected_index", [0, 1, 2, 3, 4])
def test_detect_selected_finds_lit_icon(tmp_path, selected_index):
    img_path = tmp_path / f"sel-{selected_index}.png"
    _make_image(selected_index, img_path)
    tokens = _tokens_for_labels()
    chosen = detect_selected(img_path, OPTIONS, tokens)
    assert chosen == OPTIONS[selected_index]


def test_detect_selected_returns_none_when_ambiguous(tmp_path):
    # All icons identical -> brightness gap < threshold -> None.
    img = Image.new("RGB", (IMG_W, IMG_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i in range(len(OPTIONS)):
        cx = _slot_x(i)
        draw.ellipse((cx - 50, ICON_Y_PX - 50, cx + 50, ICON_Y_PX + 50), fill=(50, 50, 55))
    img_path = tmp_path / "ambiguous.png"
    img.save(img_path)
    assert detect_selected(img_path, OPTIONS, _tokens_for_labels()) is None


def test_detect_selected_missing_token_skipped(tmp_path):
    img_path = tmp_path / "missing.png"
    _make_image(2, img_path)
    # Tokens for only some of the options - detector should still pick from what it sees.
    tokens = [t for t in _tokens_for_labels() if t.text in {"Snow", "Icy"}]
    assert detect_selected(img_path, OPTIONS, tokens) == "Snow"
