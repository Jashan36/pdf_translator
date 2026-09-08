"""MockTranslationBackend — Milestone 5 point 15.

Deterministic, zero model dependencies. Lets the entire PDF pipeline
(Milestone 4) and every translation-architecture concept in this
milestone (units, protected entities, batching, error handling) be
tested without ever installing torch/transformers/IndicTransToolkit —
required so the test suite is not IndicTrans2-availability-dependent
(point 20).
"""

from __future__ import annotations

from core.translation.backend import BackendInfo
from core.translation.models import TranslationErrorCode, TranslationRequest, TranslationResult
from core.translation.registry import LANGUAGES

# A small curated table for known-good deterministic test translations
# (real, verified phrases — not placeholder gibberish) — used by the
# rendering-proof/fixture sentences already established in Milestones
# 1-4 so a mock-backed pipeline run produces text this project has
# already visually verified renders correctly.
_TABLE: dict[tuple[str, str, str], str] = {
    ("Hello", "en", "hi"): "नमस्ते",
    ("Hello", "en", "te"): "నమస్కారం",
    ("Hello", "en", "ta"): "வணக்கம்",
    ("Hello", "en", "kn"): "ನಮಸ್ಕಾರ",
    ("This is a test sentence.", "en", "hi"): "यह एक परीक्षण वाक्य है।",
    ("This is a test sentence.", "en", "te"): "ఇది ఒక పరీక్ష వాక్యం.",
    ("This is a test sentence.", "en", "ta"): "இது ஒரு சோதனை வாக்கியம்.",
    ("This is a test sentence.", "en", "kn"): "ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯ.",
}


class MockTranslationBackend:
    def __init__(self, extra_table: dict[tuple[str, str, str], str] | None = None):
        self._table = dict(_TABLE)
        if extra_table:
            self._table.update(extra_table)

    def translate(self, request: TranslationRequest) -> TranslationResult:
        if request.source_language not in LANGUAGES or request.target_language not in LANGUAGES:
            return TranslationResult(
                unit_id=request.unit_id,
                source_text=request.text,
                translated_text="",
                source_language=request.source_language,
                target_language=request.target_language,
                backend_name="mock",
                model_identifier="mock-v1",
                success=False,
                error_code=TranslationErrorCode.UNSUPPORTED_LANGUAGE,
                diagnostics=f"{request.source_language!r} or {request.target_language!r} not in language registry",
            )

        if not request.text.strip():
            return TranslationResult(
                unit_id=request.unit_id,
                source_text=request.text,
                translated_text="",
                source_language=request.source_language,
                target_language=request.target_language,
                backend_name="mock",
                model_identifier="mock-v1",
                success=False,
                error_code=TranslationErrorCode.INVALID_INPUT,
                diagnostics="empty/whitespace-only input text",
            )

        key = (request.text, request.source_language, request.target_language)
        translated = self._table.get(key)
        if translated is None:
            # Deterministic, clearly-marked fallback for anything not
            # in the curated table -- never a plausible-looking but
            # fake translation. The bracket marker makes it obvious in
            # any test/debug output that this is NOT a real
            # translation.
            translated = f"[[{request.target_language}]] {request.text}"

        return TranslationResult(
            unit_id=request.unit_id,
            source_text=request.text,
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
            backend_name="mock",
            model_identifier="mock-v1",
            success=True,
        )

    def translate_batch(self, requests: list[TranslationRequest]) -> list[TranslationResult]:
        return [self.translate(r) for r in requests]

    def supported_languages(self) -> set[str]:
        return set(LANGUAGES.keys())

    def backend_info(self) -> BackendInfo:
        return BackendInfo(
            name="mock",
            model_identifier="mock-v1",
            version="1.0",
            deterministic=True,
            device="cpu",
            notes="Deterministic lookup-table backend; no model loaded. For tests and pipeline development only.",
        )
