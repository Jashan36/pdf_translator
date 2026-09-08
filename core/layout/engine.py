"""TextFitEngine — Milestone 3's deterministic fit algorithm.

Decision path (fixed order, per this milestone's brief):

    1. preferred font @ initial_font_size on the ORIGINAL geometry
    2. -> if that fails: geometry tolerance (controlled expansion),
         same font size, scale_low=1.0 (no silent shrink)
    3. -> if that fails: binary-search font size downward (on the
         expanded rect if expansion was allowed and available, else
         on the original rect), down to (but never below) min_font_size
    4. -> if even min_font_size does not fit: NO_FIT_MIN_FONT_SIZE,
         with diagnostics computed from a generous-height probe

Word-boundary preservation and multi-line wrapping are NOT
reimplemented here -- they're `insert_htmlbox`'s own job, already
validated for word-boundary wrapping across all four target languages
in `docs/research/indic-rendering-proof.md`. This engine only decides
WHICH font size and WHICH rect to hand it; it never edits `text`
itself (only the isolated numeral-fallback copy used for rendering,
see `numerals.py`), and it never mutates a source Document Model
object.
"""

from __future__ import annotations

import math
import os

import pymupdf

from core.layout.measurer import TextMeasurer
from core.layout.models import (
    FitStatus,
    GeometryDecision,
    ScriptCategory,
    TextFitRequest,
    TextFitResult,
)
from core.layout.numerals import apply_native_digit_fallback


def _apply_safety_inset(rect: pymupdf.Rect, inset: float) -> pymupdf.Rect:
    if inset <= 0:
        return rect
    return pymupdf.Rect(rect.x0 + inset, rect.y0 + inset, rect.x1 - inset, rect.y1 - inset)


def _validate_geometry(rect: pymupdf.Rect, page_bounds: pymupdf.Rect | None) -> str | None:
    if rect.width <= 0 or rect.height <= 0:
        return f"available_rect has non-positive dimensions: {rect}"
    if rect.is_empty or rect.is_infinite:
        return f"available_rect is empty or infinite: {rect}"
    if page_bounds is not None and not page_bounds.contains(rect):
        return f"available_rect {rect} is not within page_bounds {page_bounds}"
    return None


def _expand_rect(
    rect: pymupdf.Rect,
    max_expansion_ratio: float,
    page_bounds: pymupdf.Rect | None,
    obstacle_rects: list[pymupdf.Rect],
) -> tuple[pymupdf.Rect, bool, bool]:
    """Conservative, deterministic expansion policy: grow right and
    down by `max_expansion_ratio` of the rect's own width/height,
    clamp to `page_bounds` if given, and abandon the expansion
    ENTIRELY (falling back to the unmodified rect) if the grown region
    would touch any known obstacle. This project does not attempt
    partial/clever collision avoidance in Milestone 3 -- see
    PROJECT_STATE.md's known limitations for why (no reliable way yet
    to know which direction is safe without a fuller layout pass).

    Returns (rect_to_use, expanded, abandoned_due_to_obstacle).
    """
    growth_w = rect.width * max_expansion_ratio
    growth_h = rect.height * max_expansion_ratio
    candidate = pymupdf.Rect(rect.x0, rect.y0, rect.x1 + growth_w, rect.y1 + growth_h)

    if page_bounds is not None:
        candidate = candidate & page_bounds

    if candidate == rect:
        return rect, False, False

    for obstacle in obstacle_rects:
        if candidate.intersects(obstacle):
            return rect, False, True

    return candidate, True, False


class TextFitEngine:
    """Deterministic: for a given `TextFitRequest` and a fixed
    environment (installed PyMuPDF version, font files on disk), the
    same request always produces the same `TextFitResult` -- every
    decision is arithmetic (binary search over a fixed grid) or a
    direct `insert_htmlbox` measurement, never randomized or
    order-dependent across calls."""

    def __init__(self, measurer: TextMeasurer | None = None):
        self._owns_measurer = measurer is None
        self._measurer_cache: dict[str, TextMeasurer] = {}
        self._fixed_measurer = measurer

    def _measurer_for(self, font_file: str) -> TextMeasurer:
        if self._fixed_measurer is not None:
            return self._fixed_measurer
        font_dir = os.path.dirname(font_file)
        if font_dir not in self._measurer_cache:
            self._measurer_cache[font_dir] = TextMeasurer(font_dir)
        return self._measurer_cache[font_dir]

    def fit(self, request: TextFitRequest) -> TextFitResult:
        # --- validation -----------------------------------------------
        if not os.path.isfile(request.font_file):
            return TextFitResult(
                source_id=request.source_id,
                status=FitStatus.MISSING_FONT,
                reason=f"font file not found: {request.font_file}",
            )

        geometry_error = _validate_geometry(request.available_rect, request.page_bounds)
        if geometry_error:
            return TextFitResult(
                source_id=request.source_id, status=FitStatus.INVALID_GEOMETRY, reason=geometry_error
            )

        inset_rect = _apply_safety_inset(request.available_rect, request.safety_inset)
        inset_error = _validate_geometry(inset_rect, None)
        if inset_error:
            return TextFitResult(
                source_id=request.source_id,
                status=FitStatus.INVALID_GEOMETRY,
                reason=f"safety_inset={request.safety_inset} leaves no usable area: {inset_error}",
            )

        # --- rendering-compatibility text (never the translation itself) --
        allow_horizontal_scaling = request.allow_horizontal_scaling and request.script_category != ScriptCategory.INDIC
        render_text, digit_fallback_applied = (
            apply_native_digit_fallback(request.text, request.language)
            if request.renderer_numeral_fallback
            else (request.text, False)
        )

        font_filename = os.path.basename(request.font_file)
        measurer = self._measurer_for(request.font_file)
        attempted_font_sizes: list[float] = []

        def measure_at(size: float, rect: pymupdf.Rect):
            attempted_font_sizes.append(size)
            return measurer.measure(
                render_text,
                rect,
                font_family=request.font_family,
                font_filename=font_filename,
                font_size=size,
                line_height=request.line_height,
                alignment=request.alignment,
                scale_low=1.0,  # engine controls font size explicitly -- no silent auto-shrink
            )

        usable_rect = inset_rect
        geometry = GeometryDecision(source_rect=request.available_rect, usable_rect=usable_rect)

        # --- attempt 1: preferred font, original geometry --------------
        result = measure_at(request.initial_font_size, usable_rect)
        if result.error is not None:
            return TextFitResult(
                source_id=request.source_id,
                status=FitStatus.RENDER_ERROR,
                reason=result.error,
                attempted_font_sizes=attempted_font_sizes,
                native_digit_fallback_applied=digit_fallback_applied,
                rendered_text=render_text,
            )
        if result.fits:
            return TextFitResult(
                source_id=request.source_id,
                status=FitStatus.FIT,
                final_font_size=request.initial_font_size,
                final_rect=usable_rect,
                scale=1.0,
                spare_height=result.spare_height,
                attempted_font_sizes=attempted_font_sizes,
                geometry=geometry,
                native_digit_fallback_applied=digit_fallback_applied,
                rendered_text=render_text,
            )

        # --- attempt 2: controlled geometry tolerance -------------------
        expanded = False
        if request.allow_geometry_expansion:
            expanded_rect, did_expand, abandoned = _expand_rect(
                usable_rect, request.max_expansion_ratio, request.page_bounds, request.obstacle_rects
            )
            geometry = GeometryDecision(
                source_rect=request.available_rect,
                usable_rect=expanded_rect,
                expanded=did_expand,
                expansion_abandoned_due_to_obstacle=abandoned,
            )
            if did_expand:
                usable_rect = expanded_rect
                expanded = True
                result = measure_at(request.initial_font_size, usable_rect)
                if result.fits:
                    return TextFitResult(
                        source_id=request.source_id,
                        status=FitStatus.FIT_AFTER_GEOMETRY_TOLERANCE,
                        final_font_size=request.initial_font_size,
                        final_rect=usable_rect,
                        scale=1.0,
                        spare_height=result.spare_height,
                        attempted_font_sizes=attempted_font_sizes,
                        geometry=geometry,
                        native_digit_fallback_applied=digit_fallback_applied,
                        rendered_text=render_text,
                    )

        # --- attempt 3: binary search font size (never below min) ------
        min_result = measure_at(request.min_font_size, usable_rect)
        if not min_result.fits:
            required_height = measurer.measure_required_height(
                render_text,
                usable_rect.width,
                font_family=request.font_family,
                font_filename=font_filename,
                font_size=request.min_font_size,
                line_height=request.line_height,
            )
            overflow = max(0.0, required_height - usable_rect.height)
            if overflow <= request.overflow_tolerance:
                # Within configured slack even at the minimum size --
                # accept it rather than hard-failing over a negligible
                # amount of allowed overflow.
                status = FitStatus.FIT_AFTER_BOTH if expanded else FitStatus.FIT_AFTER_FONT_REDUCTION
                return TextFitResult(
                    source_id=request.source_id,
                    status=status,
                    final_font_size=request.min_font_size,
                    final_rect=usable_rect,
                    scale=1.0,
                    overflow=overflow,
                    attempted_font_sizes=attempted_font_sizes,
                    geometry=geometry,
                    native_digit_fallback_applied=digit_fallback_applied,
                    rendered_text=render_text,
                    reason="fit within configured overflow_tolerance at min_font_size",
                )
            return TextFitResult(
                source_id=request.source_id,
                status=FitStatus.NO_FIT_MIN_FONT_SIZE,
                final_font_size=None,
                overflow=overflow,
                line_count_estimate=_estimate_line_count(
                    required_height, request.min_font_size, request.line_height
                ),
                attempted_font_sizes=attempted_font_sizes,
                geometry=geometry,
                native_digit_fallback_applied=digit_fallback_applied,
                rendered_text=render_text,
                reason=(
                    f"text does not fit even at min_font_size={request.min_font_size}; "
                    f"estimated overflow={overflow:.1f}pt"
                ),
            )

        # min_font_size fits and initial_font_size doesn't -> binary
        # search between them. Relies on the standard text-fit
        # monotonicity assumption (a size that fits also fits at any
        # smaller size) -- true in practice since less text-width/
        # height is needed as font size shrinks. Fixed iteration count
        # (not a hi-lo threshold loop) keeps this trivially bounded and
        # deterministic regardless of the chosen step/range.
        lo, hi = request.min_font_size, request.initial_font_size
        best_fit_size = request.min_font_size  # already confirmed to fit, above
        step = request.font_size_step
        max_iterations = 20
        for _ in range(max_iterations):
            if hi - lo <= step:
                break
            mid = (lo + hi) / 2
            mid_result = measure_at(mid, usable_rect)
            if mid_result.fits:
                best_fit_size = mid
                lo = mid
            else:
                hi = mid

        # Snap down to the configured step grid for a clean reported
        # size, then re-confirm -- snapping down can only make it
        # easier to fit (smaller font), never harder.
        best_fit_size = max(request.min_font_size, math.floor(best_fit_size / step) * step)
        final_result = measure_at(best_fit_size, usable_rect)
        if not final_result.fits:
            # Should not happen given the monotonicity assumption, but
            # never claim a fit that didn't actually measure as one --
            # fall back to the last confirmed-fitting size instead.
            best_fit_size = request.min_font_size
            final_result = min_result
        status = FitStatus.FIT_AFTER_BOTH if expanded else FitStatus.FIT_AFTER_FONT_REDUCTION
        return TextFitResult(
            source_id=request.source_id,
            status=status,
            final_font_size=best_fit_size,
            final_rect=usable_rect,
            scale=1.0,
            spare_height=final_result.spare_height,
            attempted_font_sizes=attempted_font_sizes,
            geometry=geometry,
            native_digit_fallback_applied=digit_fallback_applied,
            rendered_text=render_text,
            reason=f"binary search converged on {best_fit_size}pt",
        )


def _estimate_line_count(required_height: float, font_size: float, line_height: float) -> int:
    line_box = font_size * line_height
    if line_box <= 0:
        return 0
    return max(1, round(required_height / line_box))
