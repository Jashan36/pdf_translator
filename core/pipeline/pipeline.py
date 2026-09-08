"""TranslationPipeline — the transactional entry point (point 8).

    source.pdf
       |
       +----> plan (planner.py, includes fit -- Milestone 3's engine)
       |
       +----> validate (validator.py -- collision/overlap analysis)
       |
       +----> render temporary output (executor.py)
       |
       +----> verify (verifier.py)
                 |
           +-----+-----+
           |           |
         PASS         FAIL
           |           |
     final.pdf     discard temp

The source PDF is never overwritten. A `.tmp` file is only promoted to
`output_path` after verification passes; on any failure at any stage,
no output file is produced (or an already-written temp is deleted) and
a structured `PipelineResult` explains why -- never a silent partial
result (point 3's fail-safe default, point 8's transaction model).
"""

from __future__ import annotations

import os
import time

from core.pipeline.executor import MutationExecutor
from core.pipeline.models import (
    PerformanceTimings,
    PipelineResult,
    PipelineStatus,
    PlanStatus,
    WholeDocumentTranslationRequest,
)
from core.pipeline.planner import TranslationPlanner
from core.pipeline.validator import PlanValidator
from core.pipeline.verifier import DocumentVerifier


class TranslationPipeline:
    def __init__(
        self,
        planner: TranslationPlanner | None = None,
        validator: PlanValidator | None = None,
        executor: MutationExecutor | None = None,
        verifier: DocumentVerifier | None = None,
    ):
        self.planner = planner or TranslationPlanner()
        self.validator = validator or PlanValidator()
        self.executor = executor or MutationExecutor()
        self.verifier = verifier or DocumentVerifier()

    def run(self, request: WholeDocumentTranslationRequest) -> PipelineResult:
        timings = PerformanceTimings()
        t_start = time.perf_counter()

        # PLAN + FIT (Milestone 3's TextFitEngine, called per unit inside the planner)
        t = time.perf_counter()
        plan = self.planner.build_plan(request)
        timings.planning_and_fit_s = time.perf_counter() - t

        if plan.status != PlanStatus.OK and not request.mutation_config.allow_partial_output:
            timings.total_s = time.perf_counter() - t_start
            fail_status = PipelineStatus.FAILED_FIT if plan.status == PlanStatus.NO_FIT else PipelineStatus.FAILED_VALIDATION
            return PipelineResult(status=fail_status, plan=plan, reason=plan.reason, timings=timings)

        # VALIDATE PLAN (collision/overlap analysis -- point 4)
        t = time.perf_counter()
        plan = self.validator.validate(request.document, plan)
        timings.validation_s = time.perf_counter() - t

        if plan.status != PlanStatus.OK and not request.mutation_config.allow_partial_output:
            timings.total_s = time.perf_counter() - t_start
            return PipelineResult(status=PipelineStatus.FAILED_VALIDATION, plan=plan, reason=plan.reason, timings=timings)

        # MUTATE (redact all -> commit -> reinsert all -> save to .tmp)
        t = time.perf_counter()
        success, message, plan = self.executor.execute(request.source_pdf_path, plan, request.output_path)
        timings.mutation_s = time.perf_counter() - t

        if not success:
            timings.total_s = time.perf_counter() - t_start
            return PipelineResult(status=PipelineStatus.FAILED_MUTATION, plan=plan, reason=message, timings=timings)

        temp_output_path = message

        # VERIFY (structural + source-removal + pixel; OCR deferred)
        t = time.perf_counter()
        verification = self.verifier.verify(request.source_pdf_path, temp_output_path, request.document, plan)
        timings.verification_s = time.perf_counter() - t
        timings.total_s = time.perf_counter() - t_start

        if not verification.passed:
            self._discard(temp_output_path)
            return PipelineResult(
                status=PipelineStatus.FAILED_VERIFICATION,
                plan=plan,
                verification=verification,
                reason="verification failed -- see verification.checks for details",
                timings=timings,
            )

        # PASS -> promote temp to the real output path. Source untouched throughout.
        os.replace(temp_output_path, request.output_path)
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            plan=plan,
            verification=verification,
            output_path=request.output_path,
            timings=timings,
        )

    @staticmethod
    def _discard(temp_path: str) -> None:
        try:
            os.remove(temp_path)
        except OSError:
            pass
