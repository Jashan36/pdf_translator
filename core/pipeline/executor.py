"""Stage 5-6: MUTATE — the transactional PDF-mutation stage.

Recommended order (point 5), followed exactly:

    1. Load immutable source PDF (fresh, never the caller's already-open handle).
    2. Verify every planned region BEFORE touching anything (point 6) --
       page index in range, geometry sane, expected source text present.
       Any failure here aborts with ZERO mutations applied.
    3. Apply all source-text redactions.
    4. Commit redactions (`apply_redactions`, one call per affected page).
    5. Insert all translated text via the EXISTING `LayoutRenderer`
       (`core/pdf/renderer.py`) -- no second rendering system.
    6. Save to a TEMPORARY path. The source file is NEVER overwritten;
       promotion to the real output path happens only after
       verification passes (`core/pipeline/pipeline.py`).

This is the whole-document generalization of the Milestone 2 single-
block proof (`core/pdf/redact_reinsert.py`) -- same redaction/
reinsertion primitives, same `insert_htmlbox`-only rendering path,
applied across every planned unit in one open `pymupdf.Document`
session rather than one block in isolation.
"""

from __future__ import annotations

import os

import pymupdf

from core.models import TextStyle, TranslatedSpan, TranslationStatus
from core.pdf.renderer import LayoutRenderer
from core.pipeline.models import MutationStatus, PlanStatus, TranslationPlan


class MutationExecutor:
    def execute(
        self, source_pdf_path: str, plan: TranslationPlan, output_path: str
    ) -> tuple[bool, str, TranslationPlan]:
        """Returns (success, message, updated_plan). On success,
        `message` is the path to the TEMPORARY output file (not yet
        promoted). On failure, `message` is a human-readable reason and
        the source PDF has NOT been touched."""

        applicable_units = [u for u in plan.units if u.plan_status == PlanStatus.OK]
        if not applicable_units:
            return False, "no plan units are eligible for mutation (plan_status != OK for all)", plan

        pdf = pymupdf.open(source_pdf_path)
        try:
            precheck_error = self._precheck(pdf, applicable_units)
            if precheck_error:
                return False, precheck_error, plan

            self._apply_redactions(pdf, applicable_units)
            render_error = self._reinsert(pdf, applicable_units)
            if render_error:
                return False, render_error, plan

            temp_path = output_path + ".tmp"
            pdf.save(temp_path)
            return True, temp_path, plan
        finally:
            pdf.close()

    # -- stage 2: pre-mutation verification (point 6) --------------------

    def _precheck(self, pdf: pymupdf.Document, units: list) -> str | None:
        for unit in units:
            if not (0 <= unit.page_index < pdf.page_count):
                unit.mutation_status = MutationStatus.FAILED
                unit.notes = f"page_index {unit.page_index} out of range (document has {pdf.page_count} pages)"
                return f"invalid page index for {unit.source_span_id}: {unit.notes}"

            page = pdf[unit.page_index]
            if unit.source_rect.width <= 0 or unit.source_rect.height <= 0:
                unit.mutation_status = MutationStatus.FAILED
                unit.notes = f"source_rect has non-positive dimensions: {unit.source_rect}"
                return f"invalid geometry for {unit.source_span_id}: {unit.notes}"
            if not page.rect.contains(unit.source_rect):
                unit.mutation_status = MutationStatus.FAILED
                unit.notes = f"source_rect {unit.source_rect} is outside page bounds {page.rect}"
                return f"invalid geometry for {unit.source_span_id}: {unit.notes}"

            if unit.source_text.strip():
                page_text = page.get_text("text")
                if unit.source_text.strip() not in page_text:
                    unit.mutation_status = MutationStatus.FAILED
                    unit.notes = "expected source text not found on the source page before redaction"
                    return f"source-text validation failed for {unit.source_span_id}: {unit.notes}"
        return None

    # -- stage 3-4: redaction ---------------------------------------------

    def _apply_redactions(self, pdf: pymupdf.Document, units: list) -> None:
        for unit in units:
            page = pdf[unit.page_index]
            page.add_redact_annot(unit.source_rect)

        affected_pages = sorted({unit.page_index for unit in units})
        for page_index in affected_pages:
            pdf[page_index].apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE
            )

    # -- stage 5: reinsertion (LayoutRenderer only, insert_htmlbox only) --

    def _reinsert(self, pdf: pymupdf.Document, units: list) -> str | None:
        archives: dict[str, pymupdf.Archive] = {}

        for unit in units:
            page = pdf[unit.page_index]
            fit = unit.fit_result
            font_dir = os.path.dirname(unit.font_file)
            if font_dir not in archives:
                archives[font_dir] = pymupdf.Archive(font_dir)

            final_font_size = fit.final_font_size if fit and fit.final_font_size else unit.source_style.font_size
            final_rect = fit.final_rect if fit and fit.final_rect else unit.source_rect
            render_text = fit.rendered_text if fit and fit.rendered_text else unit.translated_text

            translated_span = TranslatedSpan(
                source_span_id=unit.source_span_id,
                text=render_text,
                style=TextStyle(font_name=unit.font_family, font_size=final_font_size),
                status=TranslationStatus.TRANSLATED,
            )
            font_filename = os.path.basename(unit.font_file)
            # Must exactly match the CSS TextMeasurer used while fitting
            # (core/layout/measurer.py) -- a mismatch here (e.g. a
            # missing line-height) changes insert_htmlbox's own layout
            # and can clip content that measured as fitting.
            css = (
                f"@font-face {{font-family: {unit.font_family}; src: url({font_filename});}}\n"
                f"* {{font-family: {unit.font_family}; font-size: {final_font_size}px; "
                f"line-height: {unit.line_height}; text-align: {unit.alignment};}}"
            )
            renderer = LayoutRenderer(font_archive=archives[font_dir])
            result = renderer.render_translated_block(page, translated_span, final_rect, css=css, scale_low=1.0)

            if not result.ok:
                unit.mutation_status = MutationStatus.FAILED
                unit.notes = f"render failed during mutation: {result.error or 'reported clipped'}"
                return f"render failed for {unit.source_span_id}: {unit.notes}"

            unit.mutation_status = MutationStatus.APPLIED

        return None
