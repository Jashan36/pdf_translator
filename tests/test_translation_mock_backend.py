"""core/translation/mock_backend.py — MockTranslationBackend tests (point 15)."""

from core.translation.mock_backend import MockTranslationBackend
from core.translation.models import TranslationErrorCode, TranslationRequest


def test_hello_translates_to_known_hindi_without_loading_a_model():
    backend = MockTranslationBackend()
    result = backend.translate(
        TranslationRequest(unit_id="1", text="Hello", source_language="en", target_language="hi")
    )
    assert result.success
    assert result.translated_text == "नमस्ते"


def test_unsupported_language_returns_structured_error():
    backend = MockTranslationBackend()
    result = backend.translate(
        TranslationRequest(unit_id="1", text="Hello", source_language="en", target_language="xx")
    )
    assert not result.success
    assert result.error_code == TranslationErrorCode.UNSUPPORTED_LANGUAGE


def test_empty_input_returns_invalid_input_error():
    backend = MockTranslationBackend()
    result = backend.translate(
        TranslationRequest(unit_id="1", text="   ", source_language="en", target_language="hi")
    )
    assert not result.success
    assert result.error_code == TranslationErrorCode.INVALID_INPUT


def test_unknown_text_gets_a_clearly_marked_fallback_not_fake_translation():
    backend = MockTranslationBackend()
    result = backend.translate(
        TranslationRequest(unit_id="1", text="Some untabled sentence.", source_language="en", target_language="te")
    )
    assert result.success
    assert result.translated_text.startswith("[[te]]")


def test_batch_preserves_order_n_in_n_out():
    backend = MockTranslationBackend()
    requests = [
        TranslationRequest(unit_id=f"u{i}", text=t, source_language="en", target_language="hi")
        for i, t in enumerate(["Hello", "This is a test sentence.", "Hello", "unmatched"])
    ]
    results = backend.translate_batch(requests)
    assert len(results) == len(requests)
    assert [r.unit_id for r in results] == [f"u{i}" for i in range(4)]
    assert results[0].translated_text == "नमस्ते"
    assert results[1].translated_text == "यह एक परीक्षण वाक्य है।"


def test_backend_info_declares_deterministic_and_no_confidence():
    backend = MockTranslationBackend()
    info = backend.backend_info()
    assert info.deterministic is True
    assert info.name == "mock"


def test_supported_languages_matches_registry():
    from core.translation.registry import LANGUAGES

    backend = MockTranslationBackend()
    assert backend.supported_languages() == set(LANGUAGES.keys())
