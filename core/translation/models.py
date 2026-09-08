"""Translation request/result models — Milestone 5 points 3-4.

The rest of the application knows only: source text + source language
+ target language + options -> translated text + metadata. No backend
-specific object (a HuggingFace model, a tokenizer, an IndicProcessor)
ever crosses this boundary — see `core/translation/backend.py`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TranslationErrorCode(str, Enum):
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_LOAD_FAILED = "model_load_failed"
    INVALID_INPUT = "invalid_input"
    PLACEHOLDER_MISMATCH = "placeholder_mismatch"
    OUTPUT_EMPTY = "output_empty"
    OUTPUT_TRUNCATED = "output_truncated"
    UNIT_SPLIT_FAILED = "unit_split_failed"
    TRANSLATION_RUNTIME_ERROR = "translation_runtime_error"


class TranslationContext(BaseModel):
    """What a translation request COULD carry. Point 9: establish the
    architecture without pretending IndicTrans2 consumes all of it —
    `IndicTrans2Backend` only ever reads `preceding_text`/
    `following_text` at the sentence level (matching
    `translate_paragraph`-style usage), and ignores `glossary`/
    `document_purpose` entirely for this milestone. See that adapter's
    docstring for exactly what's used."""

    preceding_text: str | None = None
    following_text: str | None = None
    block_context: str | None = None
    document_purpose: str | None = None
    glossary: dict[str, str] = Field(default_factory=dict)


class TranslationRequest(BaseModel):
    unit_id: str  # stable id -- maps back to a TranslationUnit / SourceSpan, never a positional index
    text: str
    source_language: str  # registry code, e.g. "en"
    target_language: str
    context: TranslationContext | None = None
    mode: str = "standard"
    protected_placeholders: dict[str, str] = Field(default_factory=dict)  # placeholder token -> original value; see core/translation/protected_entities.py


class TranslationResult(BaseModel):
    unit_id: str
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    backend_name: str
    model_identifier: str
    success: bool
    error_code: TranslationErrorCode | None = None
    diagnostics: str = ""
    # ONLY set when the backend itself actually reports one -- never
    # invented. Point 4's explicit instruction. Neither MockTranslationBackend
    # nor IndicTrans2Backend (beam-search decoding has no native
    # confidence score) ever populate this in this milestone.
    confidence: float | None = None
