"""Milestone 2 point 8: LayoutRenderer interface tests.

Only the interface required by a future renderer — not a full
translation pipeline. Confirms `insert_htmlbox` is the only text-
insertion path used (per Decision 7 / the accepted rendering proof).
"""

from pathlib import Path

import pymupdf

from core.models import TextStyle, TranslatedSpan, TranslationStatus
from core.pdf.renderer import LayoutRenderer

FONTS_DIR = Path(__file__).resolve().parents[1] / "fonts"


def test_render_translated_block_fits_simple_text():
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)

    translated = TranslatedSpan(
        source_span_id="s1",
        text="Hello",
        style=TextStyle(font_name="helv", font_size=14.0),
        status=TranslationStatus.TRANSLATED,
    )
    renderer = LayoutRenderer()
    result = renderer.render_translated_block(
        page,
        translated,
        pymupdf.Rect(20, 20, 200, 60),
        css="* {font-size: 14px;}",
    )

    assert result.ok
    assert result.error is None
    assert not result.clipped
    assert result.span_id == "s1"
    doc.close()


def test_render_translated_block_uses_insert_htmlbox_for_indic_text():
    """Regression guard for Decision 7: renders real Telugu text through
    LayoutRenderer with an embedded Noto font and confirms it doesn't
    clip -- if this ever silently switched to a non-shaping API, this
    would still "succeed" numerically but the point is to keep the
    only code path this project uses for Indic text on record and
    exercised by a test."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)
    font_dir = FONTS_DIR / "telugu"
    archive = pymupdf.Archive(str(font_dir))

    translated = TranslatedSpan(
        source_span_id="s2",
        text="ఇది ఒక పరీక్ష వాక్యం.",
        style=TextStyle(font_name="NotoSansTelugu", font_size=16.0),
        status=TranslationStatus.TRANSLATED,
    )
    css = (
        "@font-face {font-family: NotoSansTelugu; src: url(NotoSans-telugu.ttf);}\n"
        "* {font-family: NotoSansTelugu; font-size: 16px;}"
    )
    renderer = LayoutRenderer(font_archive=archive)
    result = renderer.render_translated_block(page, translated, pymupdf.Rect(20, 20, 380, 60), css=css)

    assert result.ok
    doc.close()


def test_render_translated_block_reports_clipping_when_content_cannot_fit():
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)

    long_text = "This sentence is far too long to fit into a tiny box. " * 10
    translated = TranslatedSpan(
        source_span_id="s3",
        text=long_text,
        style=TextStyle(font_name="helv", font_size=14.0),
    )
    renderer = LayoutRenderer()
    # scale_low=1.0 forbids any shrinking, and the box is deliberately
    # far too small -- this must report clipped, not silently truncate.
    result = renderer.render_translated_block(
        page, translated, pymupdf.Rect(20, 20, 60, 30), css="* {font-size: 14px;}", scale_low=1.0
    )

    assert result.clipped
    assert not result.ok
    doc.close()
