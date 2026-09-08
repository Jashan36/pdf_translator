"""Central language registry — Milestone 5 point 7.

Every language code used anywhere in the translation/rendering path
comes from here. Codes are FLORES-200-style (`eng_Latn`, `hin_Deva`,
...), verified against AI4Bharat's own IndicTrans2 README during the
Milestone 1 research pass (`docs/research/indictrans2.md`) — not
re-derived from memory here.

Registry entries describe what we KNOW about a language (script, font
mapping). They do NOT claim backend support — `TranslationBackend.
supported_languages()` is the only authority for whether a given
backend can actually translate into/out of a language (point 7's
explicit instruction).
"""

from __future__ import annotations

from pydantic import BaseModel

from core.layout.models import ScriptCategory


class LanguageEntry(BaseModel):
    code: str  # short internal code, e.g. "hi"
    display_name: str
    model_code: str  # FLORES-200-style code IndicTrans2 (and similar backends) expect, e.g. "hin_Deva"
    script: str
    script_category: ScriptCategory
    font_family: str | None = None  # CSS font-family name for insert_htmlbox, if a font is available
    font_file: str | None = None  # path to the font file, if downloaded (see docs/dependencies.md)


LANGUAGES: dict[str, LanguageEntry] = {
    "en": LanguageEntry(
        code="en", display_name="English", model_code="eng_Latn", script="Latin",
        script_category=ScriptCategory.LATIN, font_family="helv", font_file=None,
    ),
    "hi": LanguageEntry(
        code="hi", display_name="Hindi", model_code="hin_Deva", script="Devanagari",
        script_category=ScriptCategory.INDIC, font_family="NotoSansDevanagari",
        font_file="fonts/devanagari/NotoSans-devanagari.ttf",
    ),
    "te": LanguageEntry(
        code="te", display_name="Telugu", model_code="tel_Telu", script="Telugu",
        script_category=ScriptCategory.INDIC, font_family="NotoSansTelugu",
        font_file="fonts/telugu/NotoSans-telugu.ttf",
    ),
    "ta": LanguageEntry(
        code="ta", display_name="Tamil", model_code="tam_Taml", script="Tamil",
        script_category=ScriptCategory.INDIC, font_family="NotoSansTamil",
        font_file="fonts/tamil/NotoSans-tamil.ttf",
    ),
    "kn": LanguageEntry(
        code="kn", display_name="Kannada", model_code="kan_Knda", script="Kannada",
        script_category=ScriptCategory.INDIC, font_family="NotoSansKannada",
        font_file="fonts/kannada/NotoSans-kannada.ttf",
    ),
    "ml": LanguageEntry(
        code="ml", display_name="Malayalam", model_code="mal_Mlym", script="Malayalam",
        script_category=ScriptCategory.INDIC, font_family=None, font_file=None,  # font not yet downloaded — see docs/dependencies.md
    ),
}


def get_language(code: str) -> LanguageEntry:
    if code not in LANGUAGES:
        raise KeyError(f"{code!r} is not in the language registry — known codes: {sorted(LANGUAGES)}")
    return LANGUAGES[code]


def model_code_for(code: str) -> str:
    return get_language(code).model_code


def is_registered(code: str) -> bool:
    return code in LANGUAGES
