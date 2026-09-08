"""Milestone 3 fit fixtures.

Not a PDF file: `TextFitEngine` operates on (text, Rect, style)
directly and independently of any source document — per Milestone 2's
finding, this milestone plans against Document Model identities, not
a re-extracted PDF. These are the structured cases point J of the
Milestone 3 brief asks for (English/Telugu/Hindi/Tamil/Kannada,
mixed-script, short/long strings, tight/roomy boxes, long words,
punctuation, numbers), expressed as plain data so every test file can
share them instead of redefining ad hoc strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from core.layout.models import ScriptCategory

ROOT = Path(__file__).resolve().parents[2]

FONT_FILES = {
    "te": str(ROOT / "fonts" / "telugu" / "NotoSans-telugu.ttf"),
    "hi": str(ROOT / "fonts" / "devanagari" / "NotoSans-devanagari.ttf"),
    "ta": str(ROOT / "fonts" / "tamil" / "NotoSans-tamil.ttf"),
    "kn": str(ROOT / "fonts" / "kannada" / "NotoSans-kannada.ttf"),
}

FONT_FAMILIES = {
    "te": "NotoSansTelugu",
    "hi": "NotoSansDevanagari",
    "ta": "NotoSansTamil",
    "kn": "NotoSansKannada",
}


@dataclass
class FitCase:
    name: str
    text: str
    rect: pymupdf.Rect
    script_category: ScriptCategory
    language: str | None = None
    font_family: str = "helv"
    font_file: str = str(ROOT / "fonts" / "telugu" / "NotoSans-telugu.ttf")  # any real file; unused glyphs for Latin-only text
    initial_font_size: float = 14.0
    min_font_size: float = 8.0
    notes: str = ""


ROOMY = pymupdf.Rect(0, 0, 500, 200)
TIGHT = pymupdf.Rect(0, 0, 90, 18)
MEDIUM = pymupdf.Rect(0, 0, 220, 40)

CASES: dict[str, FitCase] = {
    "en_short": FitCase(
        name="en_short",
        text="Hello world",
        rect=ROOMY,
        script_category=ScriptCategory.LATIN,
        notes="Should fit at initial_font_size with no reduction.",
    ),
    "en_long_wraps": FitCase(
        name="en_long_wraps",
        text="This is a considerably longer sentence that should require wrapping across multiple lines within the given rectangle.",
        rect=pymupdf.Rect(0, 0, 220, 90),  # tall enough for ~4-5 wrapped lines at initial_font_size
        script_category=ScriptCategory.LATIN,
        notes="Should fit via wrapping alone (insert_htmlbox's own behavior) at initial_font_size, no reduction needed.",
    ),
    "en_long_word_no_spaces": FitCase(
        name="en_long_word_no_spaces",
        text="Supercalifragilisticexpialidocious",
        rect=TIGHT,
        script_category=ScriptCategory.LATIN,
        notes="A single unbreakable word wider than the box -- cannot wrap around whitespace; must be handled by font reduction or NO_FIT, never silent clipping.",
    ),
    "en_punctuation": FitCase(
        name="en_punctuation",
        text='Wait... really?! Yes -- of course; (see note).',
        rect=MEDIUM,
        script_category=ScriptCategory.LATIN,
    ),
    "en_numbers": FitCase(
        name="en_numbers",
        text="Price: $500.00, Qty: 25, Ratio: 3.14159",
        rect=MEDIUM,
        script_category=ScriptCategory.LATIN,
    ),
    "te_short": FitCase(
        name="te_short",
        text="ఇది ఒక పరీక్ష వాక్యం.",
        rect=ROOMY,
        script_category=ScriptCategory.INDIC,
        language="te",
        font_family=FONT_FAMILIES["te"],
        font_file=FONT_FILES["te"],
    ),
    "te_long_wraps": FitCase(
        name="te_long_wraps",
        text=(
            "ఆరోగ్యానికి సమతుల్య ఆహారం అవసరం. ఇది శరీరానికి శక్తిని ఇస్తుంది. "
            "పిల్లలకు ఇనుము చాలా ముఖ్యం. ఇది వారి ఎదుగుదలకు తోడ్పడుతుంది."
        ),
        rect=MEDIUM,
        script_category=ScriptCategory.INDIC,
        language="te",
        font_family=FONT_FAMILIES["te"],
        font_file=FONT_FILES["te"],
    ),
    "te_numbers_native_digits": FitCase(
        name="te_numbers_native_digits",
        text="ధర ₹500 మరియు సంఖ్య ౧౨౩",
        rect=ROOMY,
        script_category=ScriptCategory.INDIC,
        language="te",
        font_family=FONT_FAMILIES["te"],
        font_file=FONT_FILES["te"],
        notes="Contains native Telugu digits -- exercises the Milestone 2 renderer-compatibility fallback (numerals.py), NOT a translation rule.",
    ),
    "hi_conjuncts": FitCase(
        name="hi_conjuncts",
        text="स्वास्थ्य के लिए संतुलित आहार आवश्यक है। यह शरीर को ऊर्जा प्रदान करता है।",
        rect=MEDIUM,
        script_category=ScriptCategory.INDIC,
        language="hi",
        font_family=FONT_FAMILIES["hi"],
        font_file=FONT_FILES["hi"],
        notes="Conjunct-heavy (स्वास्थ्य, संतुलित) -- exercises real shaping, not just plain text.",
    ),
    "hi_short": FitCase(
        name="hi_short",
        text="नमस्ते",
        rect=ROOMY,
        script_category=ScriptCategory.INDIC,
        language="hi",
        font_family=FONT_FAMILIES["hi"],
        font_file=FONT_FILES["hi"],
    ),
    "ta_vowel_signs": FitCase(
        name="ta_vowel_signs",
        text="தமிழ் மொழி பேச்சு எழுத்து ஆரோக்கியம் மிகவும் முக்கியம்.",
        rect=MEDIUM,
        script_category=ScriptCategory.INDIC,
        language="ta",
        font_family=FONT_FAMILIES["ta"],
        font_file=FONT_FILES["ta"],
        notes="Exercises Tamil vowel-sign placement (மொ, பே, சு).",
    ),
    "kn_conjuncts": FitCase(
        name="kn_conjuncts",
        text="ಕರ್ನಾಟಕದ ಸಂಸ್ಕೃತಿ ಮತ್ತು ಆರೋಗ್ಯಕ್ಕೆ ಸಮತೋಲಿತ ಆಹಾರ ಅಗತ್ಯ.",
        rect=MEDIUM,
        script_category=ScriptCategory.INDIC,
        language="kn",
        font_family=FONT_FAMILIES["kn"],
        font_file=FONT_FILES["kn"],
        notes="Conjunct-heavy (ಸಂಸ್ಕೃತಿ, ಆರೋಗ್ಯಕ್ಕೆ).",
    ),
    "mixed_latin_indic": FitCase(
        name="mixed_latin_indic",
        text="COVID-19 మహమ్మారి ప్రపంచాన్ని మార్చింది. WHO మార్గదర్శకాలను జారీ చేసింది.",
        rect=MEDIUM,
        script_category=ScriptCategory.MIXED,
        language="te",
        font_family=FONT_FAMILIES["te"],
        font_file=FONT_FILES["te"],
    ),
    "tight_box_needs_reduction": FitCase(
        name="tight_box_needs_reduction",
        text="This text needs a smaller font to fit here",
        rect=pymupdf.Rect(0, 0, 140, 20),  # too tight at 18pt, but fits after reduction (unlike TIGHT, which is deliberately impossible)
        script_category=ScriptCategory.LATIN,
        initial_font_size=18,
        min_font_size=6,
    ),
    "impossible_no_fit": FitCase(
        name="impossible_no_fit",
        text="This is far too much text to ever fit in such a tiny box no matter how small the font gets, even at the minimum allowed size." * 2,
        rect=pymupdf.Rect(0, 0, 15, 8),
        script_category=ScriptCategory.LATIN,
        initial_font_size=14,
        min_font_size=10,
        notes="Deliberately impossible -- must return NO_FIT_MIN_FONT_SIZE, never a broken/clipped render.",
    ),
}
