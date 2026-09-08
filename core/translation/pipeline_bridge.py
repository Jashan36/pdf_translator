"""Bridges Milestone 5's `TranslationResult` objects into Milestone
4's `TranslationInput` — the ONLY integration point between
translation and PDF mutation (point 19). The translation backend never
touches PyMuPDF mutation, `LayoutRenderer`, or `TextFitEngine`
directly; it only produces text. This module turns that text into
ordinary Milestone-4 `TranslationInput` objects the existing pipeline
already knows how to plan/validate/mutate/verify — nothing about
Milestone 4 itself changes.
"""

from __future__ import annotations

from core.pipeline.models import TranslationInput
from core.translation.models import TranslationResult
from core.translation.registry import get_language
from core.translation.units import TranslationUnit


def build_pipeline_translations(
    units: list[TranslationUnit],
    results: list[TranslationResult],
    target_language: str,
) -> dict[str, TranslationInput]:
    """Only successful results become pipeline `TranslationInput`s — a
    failed `TranslationResult` is simply omitted. Milestone 4's own
    fail-safe default (point 3 there) then means those spans are never
    touched unless the caller explicitly configures
    `MutationConfig.allow_partial_output` — this bridge doesn't decide
    that itself, it only supplies what successfully translated.

    Known limitation (see `units.py`): for a multi-span unit, the
    translated text is mapped onto the FIRST member span's bbox only —
    Milestone 4's pipeline plans one region per `SourceSpan.span_id`,
    and extending it to a combined multi-span region is out of scope
    for this milestone (no fixture currently exercises this case).
    """
    lang_entry = get_language(target_language)
    units_by_id = {unit.unit_id: unit for unit in units}

    translations: dict[str, TranslationInput] = {}
    for result in results:
        if not result.success:
            continue
        unit = units_by_id.get(result.unit_id)
        if unit is None:
            continue
        if not lang_entry.font_family or not lang_entry.font_file:
            continue  # no renderer font configured for this language yet -- cannot safely produce a TranslationInput

        translations[unit.unit_id] = TranslationInput(
            source_span_id=unit.unit_id,
            translated_text=result.translated_text,
            target_language=target_language,
            script_category=lang_entry.script_category,
            font_family=lang_entry.font_family,
            font_file=lang_entry.font_file,
        )
    return translations
