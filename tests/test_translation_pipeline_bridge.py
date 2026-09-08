"""core/translation/pipeline_bridge.py — translation-to-Milestone-4 bridge tests."""

import pymupdf

from core.translation.models import TranslationErrorCode, TranslationResult
from core.translation.pipeline_bridge import build_pipeline_translations
from core.translation.units import TranslationUnit


def _unit(unit_id) -> TranslationUnit:
    return TranslationUnit(
        unit_id=unit_id, text="source", source_language="en", span_ids=[unit_id],
        page_index=0, bbox=pymupdf.Rect(0, 0, 100, 20),
    )


def _success(unit_id, text="translated") -> TranslationResult:
    return TranslationResult(
        unit_id=unit_id, source_text="source", translated_text=text, source_language="en",
        target_language="hi", backend_name="mock", model_identifier="mock-v1", success=True,
    )


def _failure(unit_id) -> TranslationResult:
    return TranslationResult(
        unit_id=unit_id, source_text="source", translated_text="", source_language="en",
        target_language="hi", backend_name="mock", model_identifier="mock-v1", success=False,
        error_code=TranslationErrorCode.OUTPUT_EMPTY,
    )


def test_successful_results_become_pipeline_translation_inputs():
    units = [_unit("u0"), _unit("u1")]
    results = [_success("u0"), _success("u1")]
    translations = build_pipeline_translations(units, results, "hi")
    assert set(translations) == {"u0", "u1"}
    assert translations["u0"].translated_text == "translated"
    assert translations["u0"].font_family == "NotoSansDevanagari"


def test_failed_results_are_omitted_not_passed_through_as_broken_input():
    units = [_unit("u0"), _unit("u1")]
    results = [_success("u0"), _failure("u1")]
    translations = build_pipeline_translations(units, results, "hi")
    assert "u0" in translations
    assert "u1" not in translations


def test_language_with_no_font_configured_is_skipped():
    units = [_unit("u0")]
    results = [_success("u0")]
    translations = build_pipeline_translations(units, results, "ml")  # Malayalam has no font yet
    assert translations == {}
