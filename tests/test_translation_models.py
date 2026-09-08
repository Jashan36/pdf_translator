"""core/translation/models.py — request/result model + serialization tests."""

from core.translation.models import (
    TranslationContext,
    TranslationErrorCode,
    TranslationRequest,
    TranslationResult,
)


def test_translation_request_round_trips_through_json():
    request = TranslationRequest(
        unit_id="p1_b0_l0_s0",
        text="Hello world",
        source_language="en",
        target_language="hi",
        context=TranslationContext(preceding_text="Intro.", following_text="Outro."),
    )
    restored = TranslationRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_translation_result_round_trips_through_json():
    result = TranslationResult(
        unit_id="p1_b0_l0_s0",
        source_text="Hello",
        translated_text="नमस्ते",
        source_language="en",
        target_language="hi",
        backend_name="mock",
        model_identifier="mock-v1",
        success=True,
    )
    restored = TranslationResult.model_validate_json(result.model_dump_json())
    assert restored == result


def test_confidence_defaults_to_none_never_invented():
    result = TranslationResult(
        unit_id="x", source_text="a", translated_text="b", source_language="en",
        target_language="hi", backend_name="mock", model_identifier="mock-v1", success=True,
    )
    assert result.confidence is None


def test_error_result_carries_a_structured_code():
    result = TranslationResult(
        unit_id="x", source_text="a", translated_text="", source_language="en",
        target_language="zz", backend_name="mock", model_identifier="mock-v1",
        success=False, error_code=TranslationErrorCode.UNSUPPORTED_LANGUAGE,
    )
    assert result.success is False
    assert result.error_code == TranslationErrorCode.UNSUPPORTED_LANGUAGE
