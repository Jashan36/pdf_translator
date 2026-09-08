"""Shared helpers for Milestone 4 pipeline tests.

Loads `tests/fixtures/pipeline_multilingual.pdf` (built by
`scripts/fixtures/build_pipeline_fixture.py`) and provides small
builders for `TranslationInput`/`WholeDocumentTranslationRequest` so
individual test files don't repeat this boilerplate. Spans are looked
up by TEXT CONTENT, not a hardcoded span_id -- consistent with
Milestone 2's finding that block/span identity should be resolved
freshly from an extraction rather than assumed stable across runs, and
with how `test_redaction_reinsertion.py` already does this.
"""

from __future__ import annotations

from pathlib import Path

from core.layout.models import ScriptCategory
from core.models import Document
from core.pdf.extractor import extract_document
from core.pipeline.models import (
    FitConfig,
    MutationConfig,
    RenderConfig,
    TranslationInput,
    WholeDocumentTranslationRequest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "pipeline_multilingual.pdf"

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


def load_fixture_document() -> Document:
    return extract_document(str(FIXTURE_PATH))


def find_span_id(document: Document, text_fragment: str, page_index: int = 0) -> str:
    for span in document.pages[page_index].source_spans:
        if text_fragment in span.text:
            return span.span_id
    raise ValueError(f"no span containing {text_fragment!r} on page {page_index}")


def make_translation(span_id: str, text: str, language: str, script: ScriptCategory = ScriptCategory.INDIC) -> TranslationInput:
    return TranslationInput(
        source_span_id=span_id,
        translated_text=text,
        target_language=language,
        script_category=script,
        font_family=FONT_FAMILIES.get(language, "helv"),
        font_file=FONT_FILES.get(language, FONT_FILES["te"]),
    )


def make_request(
    document: Document,
    translations: dict[str, TranslationInput],
    output_path: str,
    *,
    allow_geometry_expansion: bool = True,
    allow_partial_output: bool = False,
    min_font_size: float = 6.0,
) -> WholeDocumentTranslationRequest:
    return WholeDocumentTranslationRequest(
        document=document,
        source_pdf_path=str(FIXTURE_PATH),
        translations=translations,
        output_path=output_path,
        render_config=RenderConfig(min_font_size=min_font_size),
        fit_config=FitConfig(allow_geometry_expansion=allow_geometry_expansion),
        mutation_config=MutationConfig(allow_partial_output=allow_partial_output),
    )
