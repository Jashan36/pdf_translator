"""TranslationService — orchestrates protection, splitting, batching,
restoration, and quality gates around a raw `TranslationBackend`
(points 6, 10, 11, 13).

    TranslationUnit
        -> protect placeholders (protected_entities.py)
        -> split if too long (splitting.py), never silently truncate
        -> ONE batched backend.translate_batch() call across every
           segment of every unit (point 10 — never one call per span
           if the backend supports batching)
        -> restore placeholders per segment
        -> reassemble segments back into one TranslationResult per unit
        -> quality gates (non-empty, placeholders restored, no stray
           control characters) before a result is allowed to be
           `success=True`

A backend only ever sees already-protected, already-segment-sized
text and never knows about units, placeholders, or splitting — those
concerns stay entirely in this module, keeping `TranslationBackend`
implementations simple (point 3: backends only translate text).
"""

from __future__ import annotations

from core.translation.backend import TranslationBackend
from core.translation.models import TranslationContext, TranslationErrorCode, TranslationRequest, TranslationResult
from core.translation.protected_entities import protect, restore
from core.translation.splitting import UnitSplitter
from core.translation.units import TranslationUnit


def _has_unexpected_control_chars(text: str) -> bool:
    return any(ord(c) < 32 and c not in "\n\t\r" for c in text)


class TranslationService:
    def __init__(self, backend: TranslationBackend, splitter: UnitSplitter | None = None):
        self.backend = backend
        self.splitter = splitter or UnitSplitter()

    def translate_units(
        self,
        units: list[TranslationUnit],
        target_language: str,
        context_by_unit: dict[str, TranslationContext] | None = None,
    ) -> list[TranslationResult]:
        """Returns exactly one `TranslationResult` per input unit, in
        the SAME order as `units` (point 10's "N inputs -> N outputs,
        verify ordering" requirement, satisfied by construction: this
        method iterates `units` once, in order, and appends exactly
        one result per iteration)."""
        info = self.backend.backend_info()
        context_by_unit = context_by_unit or {}

        split_failed: set[str] = set()
        requests: list[TranslationRequest] = []
        # Parallel to `requests`: which unit/segment/placeholders each request belongs to.
        request_plan: list[tuple[TranslationUnit, int, dict[str, str]]] = []

        for unit in units:
            protected_text, placeholders = protect(unit.text)
            segments = self.splitter.split(protected_text)
            if segments is None:
                split_failed.add(unit.unit_id)
                continue
            for index, segment in enumerate(segments):
                requests.append(
                    TranslationRequest(
                        unit_id=f"{unit.unit_id}__seg{index}",
                        text=segment,
                        source_language=unit.source_language,
                        target_language=target_language,
                        context=context_by_unit.get(unit.unit_id),
                    )
                )
                request_plan.append((unit, index, placeholders))

        raw_results = self.backend.translate_batch(requests) if requests else []

        segments_by_unit: dict[str, list[tuple[int, TranslationResult]]] = {}
        placeholders_by_unit: dict[str, dict[str, str]] = {}
        for (unit, seg_index, placeholders), raw in zip(request_plan, raw_results):
            segments_by_unit.setdefault(unit.unit_id, []).append((seg_index, raw))
            placeholders_by_unit[unit.unit_id] = placeholders

        results: list[TranslationResult] = []
        for unit in units:
            if unit.unit_id in split_failed:
                results.append(
                    TranslationResult(
                        unit_id=unit.unit_id,
                        source_text=unit.text,
                        translated_text="",
                        source_language=unit.source_language,
                        target_language=target_language,
                        backend_name=info.name,
                        model_identifier=info.model_identifier,
                        success=False,
                        error_code=TranslationErrorCode.UNIT_SPLIT_FAILED,
                        diagnostics=f"unit exceeds {self.splitter.max_chars} chars with no safe sentence-boundary split point",
                    )
                )
                continue

            ordered_segments = sorted(segments_by_unit.get(unit.unit_id, []), key=lambda item: item[0])
            failed_segment = next((r for _, r in ordered_segments if not r.success), None)
            if failed_segment is not None:
                results.append(
                    TranslationResult(
                        unit_id=unit.unit_id,
                        source_text=unit.text,
                        translated_text="",
                        source_language=unit.source_language,
                        target_language=target_language,
                        backend_name=failed_segment.backend_name,
                        model_identifier=failed_segment.model_identifier,
                        success=False,
                        error_code=failed_segment.error_code,
                        diagnostics=failed_segment.diagnostics,
                    )
                )
                continue

            combined = " ".join(r.translated_text for _, r in ordered_segments)
            restored, all_present = restore(combined, placeholders_by_unit.get(unit.unit_id, {}))

            results.append(self._apply_quality_gates(unit, target_language, info, restored, all_present))

        return results

    def _apply_quality_gates(self, unit, target_language, info, restored, all_present) -> TranslationResult:
        """Point 13: non-empty output, placeholder preservation, no
        stray control characters. Semantic quality scoring is
        explicitly out of scope for this milestone."""
        base = dict(
            unit_id=unit.unit_id,
            source_text=unit.text,
            translated_text=restored,
            source_language=unit.source_language,
            target_language=target_language,
            backend_name=info.name,
            model_identifier=info.model_identifier,
        )

        if not restored.strip():
            return TranslationResult(
                **{**base, "translated_text": ""},
                success=False,
                error_code=TranslationErrorCode.OUTPUT_EMPTY,
                diagnostics="translated output was empty after placeholder restoration",
            )
        if not all_present:
            return TranslationResult(
                **base,
                success=False,
                error_code=TranslationErrorCode.PLACEHOLDER_MISMATCH,
                diagnostics="one or more protected-entity placeholders were not found in the backend's output",
            )
        if _has_unexpected_control_chars(restored):
            return TranslationResult(
                **base,
                success=False,
                error_code=TranslationErrorCode.TRANSLATION_RUNTIME_ERROR,
                diagnostics="output contains unexpected control characters",
            )

        return TranslationResult(**base, success=True)
