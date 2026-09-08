"""core/pipeline/validator.py — overlap/collision analysis tests (point 4)."""

import pymupdf

from core.layout.models import FitStatus, ScriptCategory
from core.models import TextStyle
from core.pipeline.models import PlanStatus, PlannedTranslation, TranslationPlan
from core.pipeline.validator import PlanValidator
from tests.fixtures.pipeline_cases import find_span_id, load_fixture_document


def _unit(span_id, page_index, source_rect, final_rect, style=None) -> PlannedTranslation:
    from core.layout.models import TextFitResult

    return PlannedTranslation(
        source_span_id=span_id,
        page_index=page_index,
        source_text="x",
        translated_text="y",
        source_rect=source_rect,
        source_style=style or TextStyle(),
        target_language="te",
        script_category=ScriptCategory.INDIC,
        font_family="NotoSansTelugu",
        font_file="fonts/telugu/NotoSans-telugu.ttf",
        fit_result=TextFitResult(source_id=span_id, status=FitStatus.FIT, final_rect=final_rect, final_font_size=14),
        plan_status=PlanStatus.OK,
    )


def test_no_collisions_when_rects_are_independent():
    document = load_fixture_document()
    units = [
        _unit("a", 0, pymupdf.Rect(0, 0, 50, 20), pymupdf.Rect(0, 0, 50, 20)),
        _unit("b", 0, pymupdf.Rect(0, 100, 50, 120), pymupdf.Rect(0, 100, 50, 120)),
    ]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)
    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.OK
    assert result.collisions == []


def test_translated_overlap_detected():
    document = load_fixture_document()
    units = [
        _unit("a", 0, pymupdf.Rect(0, 0, 50, 20), pymupdf.Rect(0, 0, 50, 20)),
        _unit("b", 0, pymupdf.Rect(200, 200, 250, 220), pymupdf.Rect(10, 5, 60, 25)),  # overlaps "a"'s final rect
    ]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)
    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.COLLISION
    assert any(c.kind == "translated_overlap" for c in result.collisions)


def test_expansion_outside_page_bounds_detected():
    document = load_fixture_document()
    page = document.pages[0]
    huge_rect = pymupdf.Rect(page.mediabox.x1 - 10, page.mediabox.y1 - 10, page.mediabox.x1 + 100, page.mediabox.y1 + 100)
    units = [_unit("a", 0, pymupdf.Rect(page.mediabox.x1 - 10, page.mediabox.y1 - 10, page.mediabox.x1 - 5, page.mediabox.y1 - 5), huge_rect)]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)
    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.COLLISION
    assert any(c.kind == "expansion_outside_page" for c in result.collisions)


def test_expansion_into_untouched_source_block_detected():
    document = load_fixture_document()
    hindi_span_id = find_span_id(document, "परीक्षण")
    hindi_span = next(s for s in document.pages[0].source_spans if s.span_id == hindi_span_id)

    telugu_span_id = find_span_id(document, "పరీక్ష")
    telugu_span = next(s for s in document.pages[0].source_spans if s.span_id == telugu_span_id)

    # Expand the Telugu unit's final rect so it newly overlaps the (untouched) Hindi span.
    expanded = pymupdf.Rect(telugu_span.bbox.x0, telugu_span.bbox.y0, telugu_span.bbox.x1, hindi_span.bbox.y1 + 5)
    units = [_unit(telugu_span_id, 0, telugu_span.bbox, expanded)]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)

    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.COLLISION
    assert any(c.kind == "expansion_into_source_block" and c.other_id == hindi_span_id for c in result.collisions)


def test_preexisting_overlap_is_not_flagged():
    """point 4's important distinction: a source block that ALREADY
    legitimately overlapped something must not be flagged just because
    the (unchanged) rect still overlaps it."""
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    span = next(s for s in document.pages[0].source_spans if s.span_id == span_id)
    image = document.pages[0].images[0]

    # Pretend this span's ORIGINAL geometry already overlapped the image
    # (simulate by using the image's own bbox as both source and final rect).
    units = [_unit(span_id, 0, image.bbox, image.bbox)]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)

    result = PlanValidator().validate(document, plan)
    # No NEW overlap was introduced (final == source), so this must not be flagged.
    assert not any(c.kind == "image_conflict" for c in result.collisions)


def test_image_conflict_detected_when_newly_introduced():
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    span = next(s for s in document.pages[0].source_spans if s.span_id == span_id)
    image = document.pages[0].images[0]

    units = [_unit(span_id, 0, span.bbox, image.bbox)]  # final rect jumps onto the image; source did not overlap it
    plan = TranslationPlan(units=units, status=PlanStatus.OK)

    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.COLLISION
    assert any(c.kind == "image_conflict" for c in result.collisions)


def test_drawing_conflict_detected_when_newly_introduced():
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    span = next(s for s in document.pages[0].source_spans if s.span_id == span_id)
    drawing = document.pages[0].drawings[0]

    units = [_unit(span_id, 0, span.bbox, drawing.bbox)]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)

    result = PlanValidator().validate(document, plan)
    assert result.status == PlanStatus.COLLISION
    assert any(c.kind == "drawing_conflict" for c in result.collisions)


def test_validator_does_not_mutate_document_model():
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    span = next(s for s in document.pages[0].source_spans if s.span_id == span_id)
    original_bbox = pymupdf.Rect(span.bbox)

    units = [_unit(span_id, 0, span.bbox, pymupdf.Rect(0, 0, 10, 10))]
    plan = TranslationPlan(units=units, status=PlanStatus.OK)
    PlanValidator().validate(document, plan)

    assert span.bbox == original_bbox
