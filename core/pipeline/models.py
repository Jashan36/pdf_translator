"""Milestone 4 — whole-document pipeline models.

    EXTRACT -> PLAN -> FIT -> VALIDATE PLAN -> MUTATE -> RENDER -> VERIFY

Never: EXTRACT -> EDIT -> RE-EXTRACT -> EDIT -> ... (Milestone 2 proved
PyMuPDF block IDs are positional and unstable after edits — so the
(immutable) Document Model, not post-edit PDF extraction, is the
source of truth for every stage below). See
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 14.

Nothing here calls a translation engine — `TranslationInput` is
supplied by the caller (fixtures/tests in this milestone, per point
15). This module only plans/validates/records outcomes; the actual PDF
mutation is `core/pipeline/executor.py`, and reuses
`core/pdf/renderer.py`'s `LayoutRenderer` rather than a new renderer.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from core.geometry import PdfRect
from core.layout.models import ScriptCategory, TextFitResult
from core.models import Document, TextStyle


class MutationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    OK = "ok"
    NO_FIT = "no_fit"
    INVALID_SOURCE = "invalid_source"  # e.g. span_id not found in the Document Model
    COLLISION = "collision"


class PipelineStatus(str, Enum):
    SUCCESS = "success"
    FAILED_FIT = "failed_fit"
    FAILED_VALIDATION = "failed_validation"
    FAILED_MUTATION = "failed_mutation"
    FAILED_VERIFICATION = "failed_verification"


class TranslationInput(BaseModel):
    """Caller-supplied translation for one source span. Fixtures/tests
    only in this milestone — see point 15, no translation engine here."""

    source_span_id: str
    translated_text: str
    target_language: str
    script_category: ScriptCategory
    font_family: str
    font_file: str


class RenderConfig(BaseModel):
    initial_font_size: float | None = None  # None -> use the source span's own style.font_size
    min_font_size: float = 8.0
    line_height: float = 1.15
    alignment: str = "left"
    font_size_step: float = 0.5


class FitConfig(BaseModel):
    allow_geometry_expansion: bool = True
    max_expansion_ratio: float = 0.15
    overflow_tolerance: float = 0.0
    safety_inset: float = 0.0


class MutationConfig(BaseModel):
    # Point 3: fail-safe is the DEFAULT. allow_partial_output exists as
    # a documented future escape hatch, never flipped implicitly.
    allow_partial_output: bool = False


class WholeDocumentTranslationRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    document: Document  # the immutable Document Model — the ONE source of truth for geometry/identity
    source_pdf_path: str  # never mutated in place; opened fresh by the executor
    translations: dict[str, TranslationInput]  # keyed by SourceSpan.span_id, per Milestone 2's stable-ID finding
    output_path: str
    render_config: RenderConfig = Field(default_factory=RenderConfig)
    fit_config: FitConfig = Field(default_factory=FitConfig)
    mutation_config: MutationConfig = Field(default_factory=MutationConfig)


class PlannedTranslation(BaseModel):
    """One row of the TranslationPlan — everything needed to mutate
    (or refuse to mutate) one source span, without ever re-deriving
    identity from a post-edit PDF re-extraction."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_span_id: str
    page_index: int  # 0-based, matches pymupdf page indexing and Document Model page order
    source_text: str
    translated_text: str
    source_rect: PdfRect
    source_style: TextStyle
    target_language: str
    script_category: ScriptCategory
    font_family: str
    font_file: str
    line_height: float = 1.15  # carried from RenderConfig at planning time so the executor's render CSS exactly matches what TextFitEngine measured
    alignment: str = "left"
    fit_result: TextFitResult | None = None
    plan_status: PlanStatus = PlanStatus.OK
    mutation_status: MutationStatus = MutationStatus.PENDING
    notes: str = ""


class CollisionIssue(BaseModel):
    """One entry from the point-4 overlap/collision analysis. Only
    NEWLY introduced overlaps are ever reported — a source block that
    already legitimately overlapped something is not flagged (the
    "important distinction" point 4 calls out explicitly)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: str  # "translated_overlap" | "expansion_into_source_block" | "expansion_outside_page" | "image_conflict" | "drawing_conflict"
    span_id: str
    other_id: str | None = None
    rect_a: PdfRect
    rect_b: PdfRect | None = None
    detail: str = ""


class TranslationPlan(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    units: list[PlannedTranslation] = Field(default_factory=list)
    collisions: list[CollisionIssue] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.OK
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == PlanStatus.OK and not self.collisions


class VerificationCheck(BaseModel):
    """One verification result. `category` makes explicit which of
    point 9's four verification mechanisms this check uses — semantic,
    ocr, pixel, or text_layer/structural — so results are never
    conflated (point 9E's explicit requirement). `skipped` distinguishes
    "deliberately not run" (e.g. OCR, deferred per point 9D) from
    "ran and failed"."""

    name: str
    category: str  # "structural" | "text_layer" | "pixel" | "ocr" | "semantic"
    passed: bool
    skipped: bool = False
    detail: str = ""


class VerificationResult(BaseModel):
    checks: list[VerificationCheck] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if not c.skipped)


class PerformanceTimings(BaseModel):
    """Point 13. `planning_s` includes fit time -- TextFitEngine.fit()
    is called synchronously per unit inside the planner, so the two are
    not currently split out; documented here rather than faked apart.
    `mutation_s` includes both redaction and rendering/reinsertion --
    they happen inside one transactional stage (executor.py) by design
    (point 5's recommended order), so splitting them would require
    restructuring not justified by this milestone's goals."""

    planning_and_fit_s: float = 0.0
    validation_s: float = 0.0
    mutation_s: float = 0.0
    verification_s: float = 0.0
    total_s: float = 0.0


class PipelineResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: PipelineStatus
    plan: TranslationPlan | None = None
    verification: VerificationResult | None = None
    output_path: str | None = None  # set ONLY on SUCCESS -- a failed run never produces/promotes an output file
    reason: str = ""
    timings: PerformanceTimings = Field(default_factory=PerformanceTimings)

    @property
    def ok(self) -> bool:
        return self.status == PipelineStatus.SUCCESS
