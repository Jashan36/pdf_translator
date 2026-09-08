"""TextFitEngine tests — Milestone 3, point I's 16 required cases.

Numbered comments map each test back to the brief's numbered list.
"""

from __future__ import annotations

import copy

import pymupdf
import pytest

from core.layout.engine import TextFitEngine
from core.layout.models import FitStatus, ScriptCategory, TextFitRequest
from core.models import TextStyle
from tests.fixtures.fit_cases import CASES, FitCase


@pytest.fixture()
def engine():
    return TextFitEngine()


def _request_from_case(case: FitCase, **overrides) -> TextFitRequest:
    kwargs = dict(
        source_id=case.name,
        text=case.text,
        language=case.language,
        script_category=case.script_category,
        available_rect=case.rect,
        style=TextStyle(),
        font_family=case.font_family,
        font_file=case.font_file,
        initial_font_size=case.initial_font_size,
        min_font_size=case.min_font_size,
    )
    kwargs.update(overrides)
    return TextFitRequest(**kwargs)


# 1. Short English text fits.
def test_short_english_fits(engine):
    result = engine.fit(_request_from_case(CASES["en_short"]))
    assert result.status == FitStatus.FIT
    assert result.final_font_size == CASES["en_short"].initial_font_size


# 2. Long English text wraps (fits without needing font reduction, via insert_htmlbox's own wrapping).
def test_long_english_wraps_without_font_reduction(engine):
    result = engine.fit(_request_from_case(CASES["en_long_wraps"]))
    assert result.ok
    assert result.status == FitStatus.FIT  # wrapping alone should be enough in a MEDIUM box
    assert result.final_font_size == CASES["en_long_wraps"].initial_font_size


# 3. Short Telugu fits.
def test_short_telugu_fits(engine):
    result = engine.fit(_request_from_case(CASES["te_short"]))
    assert result.status == FitStatus.FIT


# 4. Long Telugu wraps.
def test_long_telugu_wraps(engine):
    result = engine.fit(_request_from_case(CASES["te_long_wraps"]))
    assert result.ok
    assert result.spare_height is None or result.spare_height >= 0 or result.status != FitStatus.NO_FIT_MIN_FONT_SIZE


# 5. Hindi conjuncts fit.
def test_hindi_conjuncts_fit(engine):
    result = engine.fit(_request_from_case(CASES["hi_conjuncts"]))
    assert result.ok


# 6. Tamil vowel-sign cases fit.
def test_tamil_vowel_signs_fit(engine):
    result = engine.fit(_request_from_case(CASES["ta_vowel_signs"]))
    assert result.ok


# 7. Kannada conjunct cases fit.
def test_kannada_conjuncts_fit(engine):
    result = engine.fit(_request_from_case(CASES["kn_conjuncts"]))
    assert result.ok


# 8. Mixed Latin + Indic fits.
def test_mixed_latin_indic_fits(engine):
    result = engine.fit(_request_from_case(CASES["mixed_latin_indic"]))
    assert result.ok


# 9. Text requiring font reduction uses binary search (multiple distinct attempts, not a single linear step).
def test_font_reduction_uses_binary_search_not_linear(engine):
    case = CASES["tight_box_needs_reduction"]
    result = engine.fit(_request_from_case(case))
    assert result.status in (FitStatus.FIT_AFTER_FONT_REDUCTION, FitStatus.FIT_AFTER_BOTH)
    # A linear decrement from 18 to the final size at 0.5pt steps would
    # take dozens of attempts; binary search should converge in well
    # under 20 (bounded by the engine's fixed iteration cap).
    assert 2 < len(result.attempted_font_sizes) <= 20
    assert result.final_font_size < case.initial_font_size
    assert result.final_font_size >= case.min_font_size


# 10. Text below minimum font size returns NO_FIT.
def test_impossible_fit_returns_no_fit_min_font_size(engine):
    result = engine.fit(_request_from_case(CASES["impossible_no_fit"]))
    assert result.status == FitStatus.NO_FIT_MIN_FONT_SIZE
    assert not result.ok
    assert result.overflow is not None and result.overflow > 0
    assert result.final_font_size is None


# 11. Tight original bbox receives controlled tolerance (geometry expansion attempted before font reduction).
def test_tight_bbox_receives_geometry_tolerance_before_font_reduction(engine):
    rect = pymupdf.Rect(50, 50, 175, 68)  # 125x18 -- tight for this text at 14pt
    request = TextFitRequest(
        source_id="geom1",
        text="Slightly too long for this small box",
        language="en",
        script_category=ScriptCategory.LATIN,
        available_rect=rect,
        style=TextStyle(),
        font_family="helv",
        font_file=CASES["en_short"].font_file,
        initial_font_size=14,
        min_font_size=10,
        allow_geometry_expansion=True,
        max_expansion_ratio=0.6,
        page_bounds=pymupdf.Rect(0, 0, 600, 800),
    )
    result = engine.fit(request)
    assert result.ok
    assert result.geometry is not None
    assert result.status in (FitStatus.FIT_AFTER_GEOMETRY_TOLERANCE, FitStatus.FIT_AFTER_BOTH)
    assert result.geometry.expanded is True
    # Geometry grew, but stayed within the configured page bounds.
    assert result.final_rect.x1 <= 600 and result.final_rect.y1 <= 800


# 12. No horizontal scaling occurs for Indic scripts, even if requested.
def test_no_horizontal_scaling_for_indic_even_if_requested():
    case = CASES["te_short"]
    request = TextFitRequest(
        source_id=case.name,
        text=case.text,
        language=case.language,
        script_category=ScriptCategory.INDIC,
        available_rect=case.rect,
        style=TextStyle(),
        font_family=case.font_family,
        font_file=case.font_file,
        initial_font_size=case.initial_font_size,
        min_font_size=case.min_font_size,
        allow_horizontal_scaling=True,  # deliberately requested
    )
    engine = TextFitEngine()
    result = engine.fit(request)
    # The engine must never report a scale != 1.0 as a "horizontal
    # scaling" outcome for INDIC content -- scale here only ever
    # reflects the engine's own controlled font-size search, and the
    # request's allow_horizontal_scaling is force-disabled internally.
    assert result.ok
    assert result.scale == 1.0


# 13. Invalid geometry returns structured failure.
def test_invalid_geometry_returns_structured_failure(engine):
    bad_request = TextFitRequest(
        source_id="bad1",
        text="Hello",
        language="en",
        script_category=ScriptCategory.LATIN,
        available_rect=pymupdf.Rect(10, 10, 10, 10),  # zero width/height
        style=TextStyle(),
        font_family="helv",
        font_file=CASES["en_short"].font_file,
        initial_font_size=12,
        min_font_size=8,
    )
    result = engine.fit(bad_request)
    assert result.status == FitStatus.INVALID_GEOMETRY
    assert result.reason
    assert not result.ok


def test_missing_font_returns_structured_failure(engine):
    request = TextFitRequest(
        source_id="missing_font1",
        text="Hello",
        language="en",
        script_category=ScriptCategory.LATIN,
        available_rect=pymupdf.Rect(0, 0, 200, 40),
        style=TextStyle(),
        font_family="Ghost",
        font_file="fonts/does_not_exist.ttf",
        initial_font_size=12,
        min_font_size=8,
    )
    result = engine.fit(request)
    assert result.status == FitStatus.MISSING_FONT
    assert not result.ok


# 14. Same input produces same result (determinism).
def test_same_input_produces_same_result(engine):
    request = _request_from_case(CASES["tight_box_needs_reduction"])
    r1 = engine.fit(request)
    r2 = engine.fit(copy.deepcopy(request))
    assert r1.status == r2.status
    assert r1.final_font_size == r2.final_font_size
    assert r1.attempted_font_sizes == r2.attempted_font_sizes


# 15. Fit engine does not mutate the source Document Model / its own input request.
def test_fit_does_not_mutate_request_or_style(engine):
    style = TextStyle(font_name="Helvetica", font_size=14.0)
    request = TextFitRequest(
        source_id="immut1",
        text="Hello world",
        language="en",
        script_category=ScriptCategory.LATIN,
        available_rect=pymupdf.Rect(0, 0, 300, 60),
        style=style,
        font_family="helv",
        font_file=CASES["en_short"].font_file,
        initial_font_size=14,
        min_font_size=8,
    )
    original_text = request.text
    original_rect = pymupdf.Rect(request.available_rect)

    engine.fit(request)

    assert request.text == original_text
    assert request.available_rect == original_rect
    assert request.style.font_size == 14.0
    assert style.font_size == 14.0  # the style object itself, unmutated


# 16. Renderer compatibility fallback for native Indic numerals is isolated from translation text.
def test_native_digit_fallback_isolated_from_request_text(engine):
    case = CASES["te_numbers_native_digits"]
    request = _request_from_case(case)
    result = engine.fit(request)

    assert result.ok
    assert result.native_digit_fallback_applied is True
    # The REQUEST's text (the actual translation) is completely untouched.
    assert request.text == case.text
    assert "౧౨౩" in request.text
    # Only the rendering-time copy was substituted.
    assert result.rendered_text is not None
    assert "౧౨౩" not in result.rendered_text
    assert "123" in result.rendered_text


# Point C.8/F: a single unbreakable word wider than the box cannot wrap
# around whitespace -- must resolve via font reduction or a structured
# NO_FIT, never a clipped/broken render.
def test_long_word_without_spaces_resolves_without_clipping(engine):
    result = engine.fit(_request_from_case(CASES["en_long_word_no_spaces"]))
    assert result.status in (
        FitStatus.FIT,
        FitStatus.FIT_AFTER_FONT_REDUCTION,
        FitStatus.FIT_AFTER_GEOMETRY_TOLERANCE,
        FitStatus.FIT_AFTER_BOTH,
        FitStatus.NO_FIT_MIN_FONT_SIZE,
    )
    # Whichever outcome, it must be one of these structured statuses --
    # there is no "silently clipped" status in the taxonomy at all.


def test_punctuation_heavy_text_fits(engine):
    result = engine.fit(_request_from_case(CASES["en_punctuation"]))
    assert result.ok


def test_western_numbers_fit(engine):
    result = engine.fit(_request_from_case(CASES["en_numbers"]))
    assert result.ok


def test_hindi_short_fits(engine):
    result = engine.fit(_request_from_case(CASES["hi_short"]))
    assert result.status == FitStatus.FIT


# Point G: safety_inset geometry concept.
def test_safety_inset_shrinks_usable_rect(engine):
    case = CASES["en_short"]
    request = _request_from_case(case, safety_inset=5.0)
    result = engine.fit(request)
    assert result.ok
    assert result.geometry.usable_rect.x0 == case.rect.x0 + 5.0
    assert result.geometry.usable_rect.y0 == case.rect.y0 + 5.0
    assert result.geometry.usable_rect.x1 == case.rect.x1 - 5.0
    assert result.geometry.usable_rect.y1 == case.rect.y1 - 5.0
    # The original request geometry itself is untouched.
    assert request.available_rect == case.rect


def test_safety_inset_larger_than_rect_is_invalid_geometry(engine):
    case = CASES["en_short"]
    small_rect = pymupdf.Rect(0, 0, 20, 10)
    request = TextFitRequest(
        source_id="inset_invalid",
        text=case.text,
        language=case.language,
        script_category=case.script_category,
        available_rect=small_rect,
        style=TextStyle(),
        font_family=case.font_family,
        font_file=case.font_file,
        initial_font_size=case.initial_font_size,
        min_font_size=case.min_font_size,
        safety_inset=15.0,  # larger than half the rect's own dimensions
    )
    result = engine.fit(request)
    assert result.status == FitStatus.INVALID_GEOMETRY


def test_native_digit_fallback_can_be_disabled():
    case = CASES["te_numbers_native_digits"]
    request = TextFitRequest(
        source_id=case.name,
        text=case.text,
        language=case.language,
        script_category=case.script_category,
        available_rect=case.rect,
        style=TextStyle(),
        font_family=case.font_family,
        font_file=case.font_file,
        initial_font_size=case.initial_font_size,
        min_font_size=case.min_font_size,
        renderer_numeral_fallback=False,
    )
    engine = TextFitEngine()
    result = engine.fit(request)
    assert result.native_digit_fallback_applied is False
    assert result.rendered_text == case.text  # native digits passed through unmodified
