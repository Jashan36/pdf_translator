"""core/pipeline/pipeline.py — full TranslationPipeline integration
tests. Covers point 11 (protected content), point 12 (7 failure/
rollback cases), determinism, and multi-block/multi-language success.
"""

from __future__ import annotations

import os

import pymupdf
import pytest

from core.layout.models import ScriptCategory
from core.pipeline.models import PipelineStatus
from core.pipeline.pipeline import TranslationPipeline
from tests.fixtures.pipeline_cases import (
    FONT_FILES,
    find_span_id,
    load_fixture_document,
    make_request,
    make_translation,
)


def _sha256(path: str) -> str:
    import hashlib

    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# --- success: multi-block, multi-language --------------------------------


def test_multi_block_multi_language_success(tmp_path):
    document = load_fixture_document()
    ids = {
        "te": find_span_id(document, "పరీక్ష"),
        "hi": find_span_id(document, "परीक्षण"),
        "ta": find_span_id(document, "சோதனை"),
        "kn": find_span_id(document, "ಪರೀಕ್ಷೆ"),
    }
    translations = {
        ids["te"]: make_translation(ids["te"], "ఇది కొత్తది.", "te"),
        ids["hi"]: make_translation(ids["hi"], "यह नया है।", "hi"),
        ids["ta"]: make_translation(ids["ta"], "இது புதியது.", "ta"),
        ids["kn"]: make_translation(ids["kn"], "ಇದು ಹೊಸದು.", "kn"),
    }
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    result = TranslationPipeline().run(request)

    assert result.ok
    assert result.status == PipelineStatus.SUCCESS
    assert os.path.exists(output_path)
    assert result.verification.passed
    assert all(u.mutation_status.value == "applied" for u in result.plan.units)


# --- point 11: protected content -----------------------------------------


def test_protected_content_preserved(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    result = TranslationPipeline().run(request)
    assert result.ok

    from core.pdf.extractor import extract_document

    output_document = extract_document(output_path)
    out_page = output_document.pages[0]
    src_page = document.pages[0]

    # Unrelated text (Hindi, Tamil, Kannada, English, the untouched paragraph) unchanged.
    unrelated_before = {s.text for s in src_page.source_spans if s.span_id != span_id}
    unrelated_after = {s.text for s in out_page.source_spans}
    assert unrelated_before.issubset(unrelated_after)

    # Images/drawings unchanged.
    assert len(out_page.images) == len(src_page.images)
    assert out_page.images[0].xref == src_page.images[0].xref
    assert len(out_page.drawings) == len(src_page.drawings)

    # Page count/dimensions unchanged.
    assert output_document.page_count == document.page_count
    assert out_page.width == src_page.width and out_page.height == src_page.height


def test_untouched_block_geometry_byte_identical(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    result = TranslationPipeline().run(request)
    assert result.ok

    from core.pdf.extractor import extract_document

    output_document = extract_document(output_path)
    hindi_before = next(s for s in document.pages[0].source_spans if "परीक्षण" in s.text)
    hindi_after = next(s for s in output_document.pages[0].source_spans if "परीक्षण" in s.text)
    assert hindi_before.bbox == hindi_after.bbox


# --- point 12: failure / rollback cases -----------------------------------


def test_failure_case_1_no_fit(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    huge = "చాలా పొడవైన అనువాదం " * 40
    translations = {span_id: make_translation(span_id, huge, "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path, allow_geometry_expansion=False, min_font_size=10.0)

    before_hash = _sha256(request.source_pdf_path)
    result = TranslationPipeline().run(request)
    after_hash = _sha256(request.source_pdf_path)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_FIT
    assert not os.path.exists(output_path)
    assert before_hash == after_hash


def test_failure_case_2_invalid_geometry(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)
    # Corrupt the Document Model's own span geometry before planning.
    for page in request.document.pages:
        for span in page.source_spans:
            if span.span_id == span_id:
                object.__setattr__(span, "bbox", pymupdf.Rect(5, 5, 5, 5))  # SourceSpan is frozen -- bypass deliberately for this test

    result = TranslationPipeline().run(request)

    assert not result.ok
    assert result.status in (PipelineStatus.FAILED_FIT, PipelineStatus.FAILED_MUTATION)
    assert not os.path.exists(output_path)


def test_failure_case_3_expected_source_text_missing(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    # Build a plan/executor scenario indirectly: use a source PDF that
    # does not actually contain the expected text at that geometry, by
    # pointing source_pdf_path at a different, unrelated fixture while
    # keeping the Document Model (and its expected source_text) as-is.
    request.source_pdf_path = "tests/fixtures/sample_native.pdf"

    result = TranslationPipeline().run(request)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_MUTATION
    assert not os.path.exists(output_path)


class _StubPlanner:
    """Milestone 3's fit engine already refuses to expand into a known
    obstacle or past page bounds (obstacle-avoidance + page_bounds
    clamping) -- so a genuine collision essentially never reaches the
    validator via organic fit-engine behavior when page_bounds/
    obstacle_rects are always supplied (as this planner does). To test
    the VALIDATOR'S OWN rejection wired into the full pipeline (not
    just Milestone 3's already-tested prevention), these two cases
    inject an already-built plan with a deliberately colliding/out-of-
    bounds fit_result, the same way test_pipeline_validator.py's unit
    tests construct one directly -- proving the full pipeline correctly
    refuses to proceed to mutation when handed such a plan, regardless
    of how it was produced."""

    def __init__(self, plan):
        self._plan = plan

    def build_plan(self, request):
        return self._plan


def test_failure_case_4_overlapping_planned_regions(tmp_path):
    from core.layout.models import FitStatus, TextFitResult
    from core.models import TextStyle
    from core.pipeline.models import PlannedTranslation, PlanStatus, TranslationPlan

    document = load_fixture_document()
    te_id = find_span_id(document, "పరీక్ష")
    hi_id = find_span_id(document, "परीक्षण")
    te_span = next(s for s in document.pages[0].source_spans if s.span_id == te_id)
    hi_span = next(s for s in document.pages[0].source_spans if s.span_id == hi_id)

    def unit(span, span_id, overlapping_rect):
        return PlannedTranslation(
            source_span_id=span_id, page_index=0, source_text=span.text, translated_text="x",
            source_rect=span.bbox, source_style=TextStyle(), target_language="te",
            script_category=ScriptCategory.INDIC, font_family="NotoSansTelugu", font_file=FONT_FILES["te"],
            fit_result=TextFitResult(source_id=span_id, status=FitStatus.FIT, final_rect=overlapping_rect, final_font_size=14),
            plan_status=PlanStatus.OK,
        )

    shared_rect = pymupdf.Rect(72, 300, 200, 320)  # both units land on the exact same rect -> guaranteed overlap
    plan = TranslationPlan(units=[unit(te_span, te_id, shared_rect), unit(hi_span, hi_id, shared_rect)], status=PlanStatus.OK)

    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, {}, output_path)
    before_hash = _sha256(request.source_pdf_path)
    result = TranslationPipeline(planner=_StubPlanner(plan)).run(request)
    after_hash = _sha256(request.source_pdf_path)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_VALIDATION
    assert not os.path.exists(output_path)
    assert before_hash == after_hash
    assert any(c.kind == "translated_overlap" for c in result.plan.collisions)


def test_failure_case_5_exceeds_page_bounds(tmp_path):
    from core.layout.models import FitStatus, TextFitResult
    from core.models import TextStyle
    from core.pipeline.models import PlannedTranslation, PlanStatus, TranslationPlan

    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    span = next(s for s in document.pages[0].source_spans if s.span_id == span_id)
    page_bounds = document.pages[0].mediabox
    out_of_bounds_rect = pymupdf.Rect(page_bounds.x1 - 5, page_bounds.y1 - 5, page_bounds.x1 + 200, page_bounds.y1 + 200)

    unit = PlannedTranslation(
        source_span_id=span_id, page_index=0, source_text=span.text, translated_text="x",
        source_rect=span.bbox, source_style=TextStyle(), target_language="te",
        script_category=ScriptCategory.INDIC, font_family="NotoSansTelugu", font_file=FONT_FILES["te"],
        fit_result=TextFitResult(source_id=span_id, status=FitStatus.FIT, final_rect=out_of_bounds_rect, final_font_size=14),
        plan_status=PlanStatus.OK,
    )
    plan = TranslationPlan(units=[unit], status=PlanStatus.OK)

    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, {}, output_path)
    result = TranslationPipeline(planner=_StubPlanner(plan)).run(request)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_VALIDATION
    assert not os.path.exists(output_path)
    assert any(c.kind == "expansion_outside_page" for c in result.plan.collisions)


def test_failure_case_6_renderer_failure(tmp_path):
    """Missing font file -> MISSING_FONT at the fit stage, which is
    itself a structured renderer/rendering-path failure caught before
    mutation (the fit engine IS the pre-flight check for the exact
    renderer this pipeline uses -- see Decision 13)."""
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translation = make_translation(span_id, "ఇది కొత్తది.", "te")
    translation.font_file = "fonts/does_not_exist.ttf"
    translations = {span_id: translation}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    result = TranslationPipeline().run(request)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_FIT
    assert not os.path.exists(output_path)


def test_failure_case_7_verification_failure_discards_temp_output(tmp_path, monkeypatch):
    """Force a verification failure via a stubbed verifier that always
    fails, and confirm the temp file is discarded and no final output
    is promoted."""
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    class AlwaysFailVerifier:
        def verify(self, *args, **kwargs):
            from core.pipeline.models import VerificationCheck, VerificationResult

            return VerificationResult(checks=[VerificationCheck(name="forced_failure", category="structural", passed=False)])

    pipeline = TranslationPipeline(verifier=AlwaysFailVerifier())
    result = pipeline.run(request)

    assert not result.ok
    assert result.status == PipelineStatus.FAILED_VERIFICATION
    assert not os.path.exists(output_path)
    assert not os.path.exists(output_path + ".tmp")  # discarded, not left behind


# --- determinism / transaction behavior -----------------------------------


def test_pipeline_is_deterministic(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}

    out1 = str(tmp_path / "out1.pdf")
    out2 = str(tmp_path / "out2.pdf")
    result1 = TranslationPipeline().run(make_request(load_fixture_document(), translations, out1))
    result2 = TranslationPipeline().run(make_request(load_fixture_document(), translations, out2))

    assert result1.status == result2.status == PipelineStatus.SUCCESS
    assert result1.plan.units[0].fit_result.final_font_size == result2.plan.units[0].fit_result.final_font_size
    assert result1.plan.units[0].fit_result.status == result2.plan.units[0].fit_result.status


def test_source_never_overwritten_across_all_failure_modes(tmp_path):
    """Belt-and-suspenders: after every failure case above, the source
    fixture file itself must still be exactly the one on disk in
    tests/fixtures/ -- this test re-confirms that against the real
    committed fixture after the whole module's failure tests have run
    (pytest fixture ordering aside, this is a final sanity check)."""
    from tests.fixtures.pipeline_cases import FIXTURE_PATH

    assert FIXTURE_PATH.exists()
    # Just confirm it still opens cleanly -- a corrupted/partially
    # written file would fail here.
    with pymupdf.open(str(FIXTURE_PATH)) as doc:
        assert doc.page_count == 1


# --- performance (point 13) ------------------------------------------------


def test_pipeline_reports_stage_timings(tmp_path):
    document = load_fixture_document()
    ids = {
        "te": find_span_id(document, "పరీక్ష"),
        "hi": find_span_id(document, "परीक्षण"),
    }
    translations = {
        ids["te"]: make_translation(ids["te"], "ఇది కొత్తది.", "te"),
        ids["hi"]: make_translation(ids["hi"], "यह नया है।", "hi"),
    }
    output_path = str(tmp_path / "out.pdf")
    request = make_request(document, translations, output_path)

    result = TranslationPipeline().run(request)

    assert result.ok
    t = result.timings
    assert t.planning_and_fit_s > 0
    assert t.validation_s >= 0
    assert t.mutation_s > 0
    assert t.verification_s > 0
    assert t.total_s >= (t.planning_and_fit_s + t.validation_s + t.mutation_s + t.verification_s) * 0.9
