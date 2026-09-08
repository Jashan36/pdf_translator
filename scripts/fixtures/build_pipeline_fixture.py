"""Builds tests/fixtures/pipeline_multilingual.pdf — Milestone 4 point 10.

Like `build_golden_multilingual.py` (Milestone 2), Indic text blocks
are built with `insert_text(..., fontfile=...)`, NOT `insert_htmlbox`,
for byte-exact known ground truth (see that script's docstring and
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 7's Milestone-2
update for why).

Unlike the Milestone 2 fixture, boxes here are deliberately spaced far
apart (so most blocks can be translated independently without
collision) except two specifically undersized boxes used to exercise
font-reduction and geometry-tolerance paths in the pipeline tests.

Run: .venv/Scripts/python.exe scripts/fixtures/build_pipeline_fixture.py
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "tests" / "fixtures" / "pipeline_multilingual.pdf"

FONTS = {
    "telugu": str(ROOT / "fonts" / "telugu" / "NotoSans-telugu.ttf"),
    "devanagari": str(ROOT / "fonts" / "devanagari" / "NotoSans-devanagari.ttf"),
    "tamil": str(ROOT / "fonts" / "tamil" / "NotoSans-tamil.ttf"),
    "kannada": str(ROOT / "fonts" / "kannada" / "NotoSans-kannada.ttf"),
}

# Ground-truth source text.
HEADING = "Multilingual Pipeline Test"
ENGLISH_PARA = "This document exercises the whole-document translation pipeline."
TELUGU_TEXT = "ఇది ఒక పరీక్ష వాక్యం."
HINDI_TEXT = "यह एक परीक्षण वाक्य है।"
TAMIL_TEXT = "இது ஒரு சோதனை."  # short source; box is deliberately tight for the LONGER translation used in tests
KANNADA_TEXT = "ಇದು ಒಂದು ಪರೀಕ್ಷೆ."  # short source; box has room to expand for the LONGER translation used in tests
MIXED_TEXT = "COVID-19 మహమ్మారి ప్రపంచాన్ని మార్చింది."
ENGLISH_UNTOUCHED = "This paragraph is never translated and must remain byte-identical."


def build() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595.28, height=841.89)  # A4

    page.insert_text((72, 80), HEADING, fontsize=20, fontname="hebo", color=(0, 0, 0))
    page.insert_text((72, 120), ENGLISH_PARA, fontsize=12)

    # Roomy Telugu / Hindi / mixed boxes -- should fit at initial size.
    page.insert_text((72, 165), TELUGU_TEXT, fontsize=14, fontfile=FONTS["telugu"], fontname="F_te")
    page.insert_text((72, 205), HINDI_TEXT, fontsize=14, fontfile=FONTS["devanagari"], fontname="F_hi")

    # Tamil: source text is short and placed alone, with a following
    # blank gap, but the pipeline TEST will target a rect matching
    # this span's tight bbox against a much longer translated string
    # -- forcing font reduction. The actual bbox comes from extraction,
    # not hardcoded here.
    page.insert_text((72, 245), TAMIL_TEXT, fontsize=14, fontfile=FONTS["tamil"], fontname="F_ta")

    # Kannada: similar, but with open empty space to its right/below on
    # the page (nothing placed near it) so a geometry-tolerance
    # expansion has room to succeed without touching a neighbor.
    page.insert_text((72, 285), KANNADA_TEXT, fontsize=14, fontfile=FONTS["kannada"], fontname="F_kn")

    page.insert_text((72, 340), MIXED_TEXT, fontsize=14, fontfile=FONTS["telugu"], fontname="F_te2")

    # Untouched content, far from everything else, used to prove
    # protected-content preservation (point 11).
    page.insert_text((72, 620), ENGLISH_UNTOUCHED, fontsize=12)

    # Image (top-right area, well clear of the text column).
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 64, 64))
    pix.set_rect(pix.irect, (200, 30, 30))  # solid red square
    page.insert_image(pymupdf.Rect(450, 80, 514, 144), pixmap=pix)

    # Vector drawing, also well clear of the translated text column.
    page.draw_rect(pymupdf.Rect(450, 160, 514, 224), color=(0, 0, 1), fill=(0.9, 0.9, 1))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_PATH))
    doc.close()
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
