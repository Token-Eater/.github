"""Test icon-selection pixel sampling against a synthesized conditions image."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from drivelog.iconselect import detect_multiple_selected, detect_selected
from drivelog.ocr import OcrToken


IMG_W = 800
IMG_H = 1400

OPTIONS = ("Fine", "Rain", "Snow", "Icy", "Fog")

# Icon row centred near the top third of the image; labels just below.
ICON_Y_PX = 400
LABEL_Y_PX = 500


def _slot_x(i: int) -> int:
    return int((i + 0.5) * IMG_W / len(OPTIONS))


def _make_image(selected_index: int, path: Path, glyph: bool = False) -> None:
    img = Image.new("RGB", (IMG_W, IMG_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, _ in enumerate(OPTIONS):
        cx = _slot_x(i)
        colour = (130, 175, 230) if i == selected_index else (50, 50, 55)
        draw.ellipse((cx - 50, ICON_Y_PX - 50, cx + 50, ICON_Y_PX + 50), fill=colour)
        if glyph:
            # Mimic the white icon glyph (sun rays / cloud / snowflake etc).
            draw.ellipse((cx - 25, ICON_Y_PX - 25, cx + 25, ICON_Y_PX + 25), fill=(255, 255, 255))
    img.save(path)


@pytest.mark.parametrize("selected_index", [0, 2, 4])
def test_detect_selected_finds_lit_icon_with_white_glyph(tmp_path, selected_index):
    """Brightness alone would fail here because the white glyph dominates the box."""
    img_path = tmp_path / f"glyph-{selected_index}.png"
    _make_image(selected_index, img_path, glyph=True)
    tokens = _tokens_for_labels()
    assert detect_selected(img_path, OPTIONS, tokens) == OPTIONS[selected_index]


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


def _make_image_multi(selected_indices: set[int], path: Path) -> None:
    img = Image.new("RGB", (IMG_W, IMG_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, _ in enumerate(OPTIONS):
        cx = _slot_x(i)
        colour = (130, 175, 230) if i in selected_indices else (50, 50, 55)
        draw.ellipse((cx - 50, ICON_Y_PX - 50, cx + 50, ICON_Y_PX + 50), fill=colour)
    img.save(path)


def test_detect_multiple_selected_returns_all_lit(tmp_path):
    img_path = tmp_path / "multi.png"
    _make_image_multi({0, 2, 4}, img_path)
    result = detect_multiple_selected(img_path, OPTIONS, _tokens_for_labels())
    assert set(result) == {OPTIONS[0], OPTIONS[2], OPTIONS[4]}


def test_detect_multiple_selected_returns_empty_when_none_lit(tmp_path):
    img_path = tmp_path / "none.png"
    _make_image_multi(set(), img_path)
    assert detect_multiple_selected(img_path, OPTIONS, _tokens_for_labels()) == []


def test_detect_multiple_selected_returns_all_when_all_lit(tmp_path):
    """User's real case: all five road types ticked."""
    img_path = tmp_path / "all.png"
    _make_image_multi(set(range(len(OPTIONS))), img_path)
    result = detect_multiple_selected(img_path, OPTIONS, _tokens_for_labels())
    assert set(result) == set(OPTIONS)


def test_label_token_handles_merged_row():
    """Vision merges adjacent labels into one token; we should still detect the slice."""
    from drivelog.iconselect import _label_token

    # Simulate the real iPhone road row: Sealed and Unsealed standalone, then
    # the other three squashed into one merged token.
    merged_text = "Quiet Street Main Road Multi-laned"
    tokens = [
        OcrToken(text="Sealed", confidence=1.0, x=0.079, y=0.585, w=0.108, h=0.013),
        OcrToken(text="Unsealed", confidence=1.0, x=0.242, y=0.585, w=0.150, h=0.014),
        OcrToken(text=merged_text, confidence=1.0, x=0.404, y=0.585, w=0.555, h=0.018),
    ]
    # Direct hits still work
    assert _label_token(tokens, "Sealed").text == "Sealed"
    assert _label_token(tokens, "Unsealed").text == "Unsealed"

    # Quiet Street should be a virtual token at the START of the merged bbox.
    qs = _label_token(tokens, "Quiet Street")
    assert qs is not None
    assert qs.text == "Quiet Street"
    qs_x_centre = qs.x + qs.w / 2
    assert 0.45 < qs_x_centre < 0.55

    # Multi-laned should be at the END of the merged bbox.
    ml = _label_token(tokens, "Multi-laned")
    assert ml is not None
    ml_x_centre = ml.x + ml.w / 2
    assert 0.82 < ml_x_centre < 0.92


def test_label_token_word_boundary_prevents_unsealed_matching_sealed():
    """'Sealed' must not match inside 'Unsealed' via substring."""
    from drivelog.iconselect import _label_token

    tokens = [
        OcrToken(text="Unsealed", confidence=1.0, x=0.242, y=0.585, w=0.150, h=0.014),
    ]
    assert _label_token(tokens, "Sealed") is None
    assert _label_token(tokens, "Unsealed") is not None
