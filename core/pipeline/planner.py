"""Stage 1-2: PLAN + FIT — builds a complete `TranslationPlan` before
any PDF mutation happens. Reuses `core.layout.engine.TextFitEngine`
(Milestone 3) exactly as-is; this module's only job is turning a
`WholeDocumentTranslationRequest` into per-span fit requests sourced
from the Document Model, never from a re-extracted PDF.
"""

from __future__ import annotations

from core.layout.engine import TextFitEngine
from core.layout.models import TextFitRequest
from core.models import Document, SourceSpan
from core.pipeline.models import (
    PlannedTranslation,
    PlanStatus,
    TranslationPlan,
    WholeDocumentTranslationRequest,
)


class TranslationPlanner:
    def __init__(self, fit_engine: TextFitEngine | None = None):
        self.fit_engine = fit_engine or TextFitEngine()

    def build_plan(self, request: WholeDocumentTranslationRequest) -> TranslationPlan:
        span_index = self._index_spans(request.document)
        units: list[PlannedTranslation] = []

        for span_id, translation in request.translations.items():
            if span_id not in span_index:
                units.append(
                    self._invalid_source_unit(
                        span_id, translation, reason=f"span_id {span_id!r} not found in Document Model"
                    )
                )
                continue

            span, page_index = span_index[span_id]
            fit_request = self._build_fit_request(request, span, translation, page_index, span_id)
            fit_result = self.fit_engine.fit(fit_request)

            units.append(
                PlannedTranslation(
                    source_span_id=span_id,
                    page_index=page_index,
                    source_text=span.text,
                    translated_text=translation.translated_text,
                    source_rect=span.bbox,
                    source_style=span.style,
                    target_language=translation.target_language,
                    script_category=translation.script_category,
                    font_family=translation.font_family,
                    font_file=translation.font_file,
                    line_height=request.render_config.line_height,
                    alignment=request.render_config.alignment,
                    fit_result=fit_result,
                    plan_status=PlanStatus.OK if fit_result.ok else PlanStatus.NO_FIT,
                    notes="" if fit_result.ok else fit_result.reason,
                )
            )

        status, reason = self._overall_status(units)
        return TranslationPlan(units=units, status=status, reason=reason)

    # -- internals -----------------------------------------------------

    def _index_spans(self, document: Document) -> dict[str, tuple[SourceSpan, int]]:
        index: dict[str, tuple[SourceSpan, int]] = {}
        for page_index, page in enumerate(document.pages):
            for span in page.source_spans:
                index[span.span_id] = (span, page_index)
        return index

    def _build_fit_request(self, request, span, translation, page_index, span_id) -> TextFitRequest:
        rc = request.render_config
        fc = request.fit_config
        page = request.document.pages[page_index]
        return TextFitRequest(
            source_id=span_id,
            text=translation.translated_text,
            language=translation.target_language,
            script_category=translation.script_category,
            available_rect=span.bbox,
            safety_inset=fc.safety_inset,
            style=span.style,
            font_family=translation.font_family,
            font_file=translation.font_file,
            initial_font_size=rc.initial_font_size or span.style.font_size or 12.0,
            min_font_size=rc.min_font_size,
            line_height=rc.line_height,
            alignment=rc.alignment,
            overflow_tolerance=fc.overflow_tolerance,
            allow_geometry_expansion=fc.allow_geometry_expansion,
            max_expansion_ratio=fc.max_expansion_ratio,
            page_bounds=page.mediabox,
            obstacle_rects=self._obstacle_rects(page, exclude_span_id=span_id),
            font_size_step=rc.font_size_step,
        )

    def _obstacle_rects(self, page, exclude_span_id: str) -> list:
        """Everything else on the page the fit engine's own geometry-
        tolerance policy should avoid touching -- other text spans
        (translated or not; the point-4 collision analysis is a
        separate, second layer of safety after fitting, not a
        substitute for this), images, and drawings."""
        obstacles = []
        for span in page.source_spans:
            if span.span_id != exclude_span_id:
                obstacles.append(span.bbox)
        for image in page.images:
            obstacles.append(image.bbox)
        for drawing in page.drawings:
            obstacles.append(drawing.bbox)
        return obstacles

    def _invalid_source_unit(self, span_id: str, translation, reason: str) -> PlannedTranslation:
        import pymupdf

        from core.models import TextStyle

        return PlannedTranslation(
            source_span_id=span_id,
            page_index=-1,
            source_text="",
            translated_text=translation.translated_text,
            source_rect=pymupdf.Rect(0, 0, 0, 0),
            source_style=TextStyle(),
            target_language=translation.target_language,
            script_category=translation.script_category,
            font_family=translation.font_family,
            font_file=translation.font_file,
            plan_status=PlanStatus.INVALID_SOURCE,
            notes=reason,
        )

    def _overall_status(self, units: list[PlannedTranslation]) -> tuple[PlanStatus, str]:
        for unit in units:
            if unit.plan_status != PlanStatus.OK:
                return unit.plan_status, f"unit {unit.source_span_id}: {unit.notes}"
        return PlanStatus.OK, ""
