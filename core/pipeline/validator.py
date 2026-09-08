"""Stage 3: VALIDATE PLAN — point 4's overlap/collision analysis.

Runs AFTER fitting, BEFORE any PDF mutation. Deterministic safety
check, not a layout optimizer (explicitly out of scope for this
milestone). The important distinction point 4 calls out: a source
block may already legitimately overlap another object -- only NEWLY
introduced overlaps (present in the fitted rect but not in the
original source rect) are ever flagged.
"""

from __future__ import annotations

from core.models import Document
from core.pipeline.models import CollisionIssue, PlanStatus, TranslationPlan


class PlanValidator:
    def validate(self, document: Document, plan: TranslationPlan) -> TranslationPlan:
        collisions: list[CollisionIssue] = []

        units_by_page: dict[int, list] = {}
        for unit in plan.units:
            if unit.plan_status != PlanStatus.OK or unit.fit_result is None or unit.fit_result.final_rect is None:
                continue
            units_by_page.setdefault(unit.page_index, []).append(unit)

        for page_index, units in units_by_page.items():
            page = document.pages[page_index]
            translated_ids = {u.source_span_id for u in units}
            collisions.extend(self._translated_overlaps(units))
            for unit in units:
                collisions.extend(self._page_bounds_check(unit, page))
                collisions.extend(self._source_block_conflicts(unit, page, translated_ids))
                collisions.extend(self._image_conflicts(unit, page))
                collisions.extend(self._drawing_conflicts(unit, page))

        status = plan.status
        reason = plan.reason
        if collisions and status == PlanStatus.OK:
            status = PlanStatus.COLLISION
            reason = f"{len(collisions)} collision(s) detected during plan validation"

        return plan.model_copy(update={"collisions": collisions, "status": status, "reason": reason})

    # -- individual checks -----------------------------------------------

    def _translated_overlaps(self, units: list) -> list[CollisionIssue]:
        issues = []
        for i, unit_a in enumerate(units):
            rect_a = unit_a.fit_result.final_rect
            for unit_b in units[i + 1 :]:
                rect_b = unit_b.fit_result.final_rect
                if rect_a.intersects(rect_b):
                    issues.append(
                        CollisionIssue(
                            kind="translated_overlap",
                            span_id=unit_a.source_span_id,
                            other_id=unit_b.source_span_id,
                            rect_a=rect_a,
                            rect_b=rect_b,
                            detail="two translated regions overlap after fitting",
                        )
                    )
        return issues

    def _page_bounds_check(self, unit, page) -> list[CollisionIssue]:
        rect = unit.fit_result.final_rect
        if not page.mediabox.contains(rect):
            return [
                CollisionIssue(
                    kind="expansion_outside_page",
                    span_id=unit.source_span_id,
                    rect_a=rect,
                    rect_b=page.mediabox,
                    detail="fitted rect exceeds page bounds",
                )
            ]
        return []

    def _source_block_conflicts(self, unit, page, translated_ids: set[str]) -> list[CollisionIssue]:
        rect = unit.fit_result.final_rect
        issues = []
        for span in page.source_spans:
            if span.span_id in translated_ids:
                continue  # covered by _translated_overlaps
            newly_overlapping = rect.intersects(span.bbox) and not unit.source_rect.intersects(span.bbox)
            if newly_overlapping:
                issues.append(
                    CollisionIssue(
                        kind="expansion_into_source_block",
                        span_id=unit.source_span_id,
                        other_id=span.span_id,
                        rect_a=rect,
                        rect_b=span.bbox,
                        detail="translated region newly overlaps an untouched text block (not present in the original geometry)",
                    )
                )
        return issues

    def _image_conflicts(self, unit, page) -> list[CollisionIssue]:
        rect = unit.fit_result.final_rect
        issues = []
        for image in page.images:
            newly_overlapping = rect.intersects(image.bbox) and not unit.source_rect.intersects(image.bbox)
            if newly_overlapping:
                issues.append(
                    CollisionIssue(
                        kind="image_conflict",
                        span_id=unit.source_span_id,
                        other_id=image.image_id,
                        rect_a=rect,
                        rect_b=image.bbox,
                        detail="translated region newly overlaps an image",
                    )
                )
        return issues

    def _drawing_conflicts(self, unit, page) -> list[CollisionIssue]:
        rect = unit.fit_result.final_rect
        issues = []
        for drawing in page.drawings:
            newly_overlapping = rect.intersects(drawing.bbox) and not unit.source_rect.intersects(drawing.bbox)
            if newly_overlapping:
                issues.append(
                    CollisionIssue(
                        kind="drawing_conflict",
                        span_id=unit.source_span_id,
                        other_id=drawing.drawing_id,
                        rect_a=rect,
                        rect_b=drawing.bbox,
                        detail="translated region newly overlaps a vector drawing",
                    )
                )
        return issues
