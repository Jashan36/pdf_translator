"""Builds tests/fixtures/golden_multilingual.pdf — Milestone 2 point 7.

IMPORTANT: this fixture's Indic text blocks are built with
`page.insert_text(..., fontfile=...)`, NOT `page.insert_htmlbox()`.

This is deliberate, not an oversight — see
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 7's Milestone-2
update: `insert_htmlbox` shapes Indic text correctly for *rendering*
but was found to corrupt the PDF's text LAYER (`get_text()` does not
round-trip the original Unicode string), while `insert_text` with a
directly-loaded font round-trips byte-exact even though it doesn't
shape conjuncts correctly for *display*. Since this fixture exists to
test EXTRACTION correctness (byte-exact known text, per Milestone 2
point 7), not rendering quality (already proven separately by the
accepted rendering proof), `insert_text` is the right choice here.

Run: .venv/Scripts/python.exe scripts/fixtures/build_golden_multilingual.py
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "tests" / "fixtures" / "golden_multilingual.pdf"

FONTS = {
    "telugu": str(ROOT / "fonts" / "telugu" / "NotoSans-telugu.ttf"),
    "devanagari": str(ROOT / "fonts" / "devanagari" / "NotoSans-devanagari.ttf"),
    "tamil": str(ROOT / "fonts" / "tamil" / "NotoSans-tamil.ttf"),
    "kannada": str(ROOT / "fonts" / "kannada" / "NotoSans-kannada.ttf"),
}

# Ground truth text — exactly what extraction tests assert against.
TELUGU_SENTENCE = "ఇది ఒక పరీక్ష వాక్యం."
HINDI_SENTENCE = "यह एक परीक्षण वाक्य है।"
TAMIL_SENTENCE = "இது ஒரு சோதனை வாக்கியம்."
KANNADA_SENTENCE = "ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯ."
MIXED_SENTENCE = "COVID-19 మహమ్మారి ప్రపంచాన్ని మార్చింది."
HEADING = "Multilingual Test Document"
PARA_1 = "This document exercises extraction across multiple scripts."
PARA_2 = "A second English paragraph follows the multilingual block above."


def build() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595.28, height=841.89)  # A4

    page.insert_text((72, 80), HEADING, fontsize=20, fontname="hebo", color=(0, 0, 0))
    page.insert_text((72, 120), PARA_1, fontsize=12)

    page.insert_text((72, 165), TELUGU_SENTENCE, fontsize=14, fontfile=FONTS["telugu"], fontname="F_te")
    page.insert_text((72, 205), HINDI_SENTENCE, fontsize=14, fontfile=FONTS["devanagari"], fontname="F_hi")
    page.insert_text((72, 245), TAMIL_SENTENCE, fontsize=14, fontfile=FONTS["tamil"], fontname="F_ta")
    page.insert_text((72, 285), KANNADA_SENTENCE, fontsize=14, fontfile=FONTS["kannada"], fontname="F_kn")
    page.insert_text((72, 325), MIXED_SENTENCE, fontsize=14, fontfile=FONTS["telugu"], fontname="F_te2")

    page.insert_text((72, 390), PARA_2, fontsize=12)

    # A real embedded raster image (XObject), not a vector-drawn shape.
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 64, 64))
    pix.set_rect(pix.irect, (200, 30, 30))  # solid red square
    page.insert_image(pymupdf.Rect(72, 420, 136, 484), pixmap=pix)

    # A vector shape distinct from the image, for Drawing extraction.
    page.draw_rect(pymupdf.Rect(160, 420, 300, 484), color=(0, 0, 1), fill=(0.9, 0.9, 1))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_PATH))
    doc.close()
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
