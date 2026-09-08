"""Complete mock-backed PDF translation through the existing
Milestone 4 pipeline — Milestone 5 point 20's final requirement:
"The full PDF pipeline must be testable without IndicTrans2 installed."

    PDFExtractor -> Document Model -> Translation Unit Builder
    -> TranslationBackend (mock) -> TranslationResults
    -> pipeline_bridge -> Milestone 4 TranslationPipeline -> output PDF
"""

import os

from core.pdf.extractor import extract_document
from core.pipeline.models import WholeDocumentTranslationRequest
from core.pipeline.pipeline import TranslationPipeline
from core.translation.mock_backend import MockTranslationBackend
from core.translation.pipeline_bridge import build_pipeline_translations
from core.translation.service import TranslationService
from core.translation.units import build_units_from_document


def test_complete_pdf_translated_via_mock_backend_through_milestone_4(tmp_path):
    document = extract_document("tests/fixtures/pipeline_multilingual.pdf")
    units = build_units_from_document(document, source_language="en")

    # Only translate the unit whose source text is given a genuine
    # (non-fallback) table entry below -- using the mock's clearly-
    # marked fallback for everything would make some verification
    # checks fail for reasons unrelated to the pipeline itself (a
    # fallback-translated English heading still literally contains its
    # own source text as a substring; see ARCHITECTURE_DECISIONS.md
    # Decision 15 for why that's a correct verifier finding, not a bug).
    english_para = "This document exercises the whole-document translation pipeline."
    translatable_units = [u for u in units if u.text.strip() == english_para]
    assert translatable_units, "fixture must contain the expected English paragraph"

    backend = MockTranslationBackend(
        extra_table={(english_para, "en", "hi"): "यह दस्तावेज़ संपूर्ण-दस्तावेज़ अनुवाद पाइपलाइन का परीक्षण करता है।"}
    )
    service = TranslationService(backend)
    results = service.translate_units(translatable_units, target_language="hi")
    assert all(r.success for r in results)

    translations = build_pipeline_translations(translatable_units, results, "hi")
    assert translations

    from core.pipeline.models import FitConfig, RenderConfig

    output_path = str(tmp_path / "translated.pdf")
    request = WholeDocumentTranslationRequest(
        document=document,
        source_pdf_path="tests/fixtures/pipeline_multilingual.pdf",
        translations=translations,
        output_path=output_path,
        render_config=RenderConfig(min_font_size=4.0),
        fit_config=FitConfig(allow_geometry_expansion=True, max_expansion_ratio=0.5),
    )
    result = TranslationPipeline().run(request)

    assert result.ok, f"pipeline failed: {result.status} / {result.reason}"
    assert os.path.exists(output_path)
    assert result.verification.passed


def test_full_translation_architecture_uses_no_pymupdf_mutation_apis_directly():
    """Point 19: the translation backend/service/unit-builder modules
    must never import PyMuPDF mutation entry points -- only
    `core/pipeline/` and `core/pdf/renderer.py` are allowed to."""
    import ast
    import pathlib

    forbidden = {"insert_htmlbox", "add_redact_annot", "apply_redactions", "insert_text", "insert_textbox"}
    translation_dir = pathlib.Path("core/translation")
    for path in translation_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        called_names = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not (called_names & forbidden), f"{path} calls a PDF-mutation API directly: {called_names & forbidden}"
