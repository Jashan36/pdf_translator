"""Renderer-compatibility fallback for the Milestone-2 native-Indic-
digit rendering bug — explicitly NOT a translation rule.

Per `docs/research/indic-rendering-proof.md`: PyMuPDF's glyph
selection for native-script digit codepoints (Telugu U+0C66-0C6F,
Tamil U+0BE6-0BEF, Kannada U+0CE6-0CEF) is broken — confirmed via
`Font.has_glyph`/`unicode_to_glyph_name` returning correct data while
the actual inserted glyphs are wrong, reproducing identically via
`insert_text` (no HTML/CSS involved). Devanagari's native digits
(U+0966-096F) are NOT affected.

This module substitutes native digits with Western digits ONLY in a
copy of the text used for measurement/rendering. It must never be
confused with "translate numerals to Western digits" — a translator
may correctly and intentionally produce native-script digits, and
`TranslatedSpan.text` (the actual translation) is never touched by
this. Only the fit engine's internal rendering-time copy is affected,
and `TextFitResult.native_digit_fallback_applied` records whether it
happened so callers can tell the difference between "rendered exactly
as translated" and "rendered with a compatibility substitution."
"""

from __future__ import annotations

# Scripts with the confirmed PyMuPDF glyph-selection bug for native
# digits (docs/research/indic-rendering-proof.md). Devanagari (hi) is
# deliberately excluded -- its native digits rendered correctly.
_AFFECTED_LANGUAGES = frozenset({"te", "ta", "kn"})

_DIGIT_BLOCKS: dict[str, range] = {
    "te": range(0x0C66, 0x0C70),  # Telugu digits 0-9
    "ta": range(0x0BE6, 0x0BF0),  # Tamil digits 0-9
    "kn": range(0x0CE6, 0x0CF0),  # Kannada digits 0-9
}


def _build_translation_table(language: str) -> dict[int, str]:
    block = _DIGIT_BLOCKS[language]
    return {codepoint: str(digit) for digit, codepoint in enumerate(block)}


_TRANSLATION_TABLES = {lang: _build_translation_table(lang) for lang in _AFFECTED_LANGUAGES}


def needs_native_digit_fallback(language: str | None) -> bool:
    return language in _AFFECTED_LANGUAGES


def apply_native_digit_fallback(text: str, language: str | None) -> tuple[str, bool]:
    """Returns (text_for_rendering, was_modified).

    Only substitutes for languages in `_AFFECTED_LANGUAGES`, and only
    if the text actually contains a native digit from that language's
    block -- so `was_modified` is a precise, truthful signal, not a
    blanket "this language always gets touched" flag.
    """
    if language not in _AFFECTED_LANGUAGES:
        return text, False

    table = _TRANSLATION_TABLES[language]
    if not any(ord(ch) in table for ch in text):
        return text, False

    return text.translate(table), True
