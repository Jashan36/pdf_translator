"""core/translation/service.py — orchestration tests (points 6, 10, 11, 13)."""

from core.translation.mock_backend import MockTranslationBackend
from core.translation.models import TranslationErrorCode
from core.translation.service import TranslationService
from core.translation.splitting import UnitSplitter
from core.translation.units import TranslationUnit
import pymupdf


def _unit(unit_id, text, language="en") -> TranslationUnit:
    return TranslationUnit(
        unit_id=unit_id, text=text, source_language=language, span_ids=[unit_id],
        page_index=0, bbox=pymupdf.Rect(0, 0, 100, 20),
    )


def test_n_units_produce_n_results_in_order():
    service = TranslationService(MockTranslationBackend())
    units = [_unit(f"u{i}", t) for i, t in enumerate(["Hello", "This is a test sentence.", "Hello"])]
    results = service.translate_units(units, target_language="hi")
    assert len(results) == 3
    assert [r.unit_id for r in results] == ["u0", "u1", "u2"]


def test_protected_entities_survive_a_full_translate_units_round_trip():
    service = TranslationService(MockTranslationBackend())
    units = [_unit("u0", "Contact support@example.com before 15 October.")]
    results = service.translate_units(units, target_language="hi")
    assert results[0].success
    assert "support@example.com" in results[0].translated_text
    assert "October" in results[0].translated_text


def test_long_unit_is_split_and_reassembled_not_truncated():
    splitter = UnitSplitter(max_chars=30)
    service = TranslationService(MockTranslationBackend(), splitter=splitter)
    text = "This is a test sentence. This is a test sentence. This is a test sentence."
    units = [_unit("u0", text)]
    results = service.translate_units(units, target_language="hi")
    assert results[0].success
    # Content from every segment made it into the final combined result --
    # nothing was dropped by the split/reassemble round-trip.
    assert results[0].translated_text.count("यह एक परीक्षण वाक्य है।") == 3


def test_unsplittable_long_unit_returns_unit_split_failed():
    splitter = UnitSplitter(max_chars=5)
    service = TranslationService(MockTranslationBackend(), splitter=splitter)
    units = [_unit("u0", "Thisisonelongwordnobreak")]
    results = service.translate_units(units, target_language="hi")
    assert not results[0].success
    assert results[0].error_code == TranslationErrorCode.UNIT_SPLIT_FAILED


def test_unsupported_language_propagates_as_result_error():
    service = TranslationService(MockTranslationBackend())
    units = [_unit("u0", "Hello")]
    results = service.translate_units(units, target_language="xx")
    assert not results[0].success
    assert results[0].error_code == TranslationErrorCode.UNSUPPORTED_LANGUAGE


def test_placeholder_mismatch_detected_when_backend_drops_token():
    class DroppingBackend(MockTranslationBackend):
        def translate_batch(self, requests):
            results = super().translate_batch(requests)
            # Simulate a backend that strips anything looking like our placeholder tokens.
            import re

            for r in results:
                r.translated_text = re.sub(r"__PROT_\w+_\d+__", "", r.translated_text)
            return results

    service = TranslationService(DroppingBackend())
    units = [_unit("u0", "Visit https://example.com today.")]
    results = service.translate_units(units, target_language="hi")
    assert not results[0].success
    assert results[0].error_code == TranslationErrorCode.PLACEHOLDER_MISMATCH


def test_empty_backend_output_becomes_output_empty_error():
    class EmptyBackend(MockTranslationBackend):
        def translate_batch(self, requests):
            results = super().translate_batch(requests)
            for r in results:
                r.translated_text = ""
            return results

    service = TranslationService(EmptyBackend())
    units = [_unit("u0", "Hello")]
    results = service.translate_units(units, target_language="hi")
    assert not results[0].success
    assert results[0].error_code == TranslationErrorCode.OUTPUT_EMPTY


def test_batching_sends_all_segments_in_one_backend_call():
    calls = []

    class CountingBackend(MockTranslationBackend):
        def translate_batch(self, requests):
            calls.append(len(requests))
            return super().translate_batch(requests)

    service = TranslationService(CountingBackend())
    units = [_unit(f"u{i}", "Hello") for i in range(5)]
    service.translate_units(units, target_language="hi")
    assert calls == [5]  # one batched call for all 5 units, not 5 separate calls


def test_service_never_mutates_input_units():
    units = [_unit("u0", "Hello")]
    original_text = units[0].text
    TranslationService(MockTranslationBackend()).translate_units(units, target_language="hi")
    assert units[0].text == original_text
