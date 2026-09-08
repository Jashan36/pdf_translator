"""core/pipeline/verifier.py — verification-stage tests (point 9)."""

from core.pipeline.executor import MutationExecutor
from core.pipeline.planner import TranslationPlanner
from core.pipeline.verifier import DocumentVerifier
from tests.fixtures.pipeline_cases import find_span_id, load_fixture_document, make_request, make_translation


def _successful_mutation(tmp_path, span_text_fragment="పరీక్ష", language="te", translated="ఇది కొత్తది."):
    document = load_fixture_document()
    span_id = find_span_id(document, span_text_fragment)
    translations = {span_id: make_translation(span_id, translated, language)}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)
    success, temp_path, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)
    assert success
    return document, request, plan, temp_path


def test_successful_mutation_passes_verification(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    assert result.passed
    assert all(c.category in ("structural", "text_layer", "pixel", "ocr") for c in result.checks)


def test_every_check_declares_its_category(tmp_path):
    """point 9E: never conflate verification mechanisms -- every check must self-report which kind it is."""
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    for check in result.checks:
        assert check.category, f"check {check.name} has no category"


def test_protected_images_and_drawings_verified_unchanged(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    image_checks = [c for c in result.checks if "image" in c.name and c.category == "pixel"]
    drawing_checks = [c for c in result.checks if "drawing" in c.name and c.category == "pixel"]
    assert image_checks and all(c.passed for c in image_checks)
    assert drawing_checks and all(c.passed for c in drawing_checks)


def test_translated_region_pixel_change_detected(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    changed_checks = [c for c in result.checks if c.name.startswith("translated_region_changed_")]
    assert changed_checks and all(c.passed for c in changed_checks)


def test_source_removal_check_uses_text_layer_category_and_is_labeled_absence_only(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    removal_checks = [c for c in result.checks if c.name.startswith("source_text_removed_")]
    assert removal_checks
    for c in removal_checks:
        assert c.category == "text_layer"
        assert "does NOT confirm" in c.detail  # honesty about what this check can and can't prove


def test_ocr_check_is_skipped_not_silently_omitted(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    ocr_checks = [c for c in result.checks if c.category == "ocr"]
    assert len(ocr_checks) == 1
    assert ocr_checks[0].skipped is True
    # A skipped check must not count toward pass/fail either way, but must still be visible.
    assert result.passed  # overall result unaffected by a skipped check


def test_output_missing_fails_gracefully():
    document = load_fixture_document()
    from core.pipeline.models import TranslationPlan

    result = DocumentVerifier().verify("tests/fixtures/pipeline_multilingual.pdf", "does_not_exist.pdf", document, TranslationPlan())
    assert not result.passed
    assert any(c.name == "output_opens" and not c.passed for c in result.checks)


def test_unrelated_content_preserved_check_passes_for_untouched_paragraph(tmp_path):
    document, request, plan, temp_path = _successful_mutation(tmp_path)
    result = DocumentVerifier().verify(request.source_pdf_path, temp_path, document, plan)
    preserved_checks = [c for c in result.checks if "unrelated_text_preserved" in c.name]
    assert preserved_checks and all(c.passed for c in preserved_checks)
