"""Milestone 3 — Text-Fit Engine models.

Core principle (CLAUDE.md / this milestone's brief):

    AI determines WHAT the translated text says.
    The text-fit engine determines HOW that text can physically fit.
    The renderer remains deterministic.

Nothing in this module (or `engine.py`/`measurer.py`) makes a
translation decision or mutates a source PDF. `TextFitRequest` takes
already-translated text as input; `TextFitResult` is a plan a renderer
can execute later — fitting is provably separate from rendering (see
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 8).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from core.geometry import PdfRect
from core.models import TextStyle


class ScriptCategory(str, Enum):
    """Coarse script classification the fit engine treats differently.

    INDIC scripts (Telugu/Devanagari/Tamil/Kannada/Malayalam, per the
    master plan's target list) must NEVER be horizontally scaled — per
    `docs/research/pdf-typography.md`/`layout-fitting.md`, doing so
    distorts HarfBuzz-computed mark/conjunct positions without
    re-shaping. This is enforced by the engine regardless of what a
    caller passes for `allow_horizontal_scaling`.
    """

    LATIN = "latin"
    INDIC = "indic"
    MIXED = "mixed"
    OTHER = "other"


class RenderingMode(str, Enum):
    """The only supported rendering path is `insert_htmlbox` — see
    Decision 7: the classic PyMuPDF text APIs (`insert_text`,
    `insert_textbox`, `TextWriter`) are not shaping-capable for Indic
    scripts and must never be used for translated content."""

    HTMLBOX = "htmlbox"


class FitStatus(str, Enum):
    FIT = "fit"
    FIT_AFTER_GEOMETRY_TOLERANCE = "fit_after_geometry_tolerance"
    FIT_AFTER_FONT_REDUCTION = "fit_after_font_reduction"
    FIT_AFTER_BOTH = "fit_after_both"
    NO_FIT_MIN_FONT_SIZE = "no_fit_min_font_size"
    INVALID_GEOMETRY = "invalid_geometry"
    MISSING_FONT = "missing_font"
    RENDER_ERROR = "render_error"


# Statuses in which the engine found a usable plan.
_OK_STATUSES = frozenset(
    {
        FitStatus.FIT,
        FitStatus.FIT_AFTER_GEOMETRY_TOLERANCE,
        FitStatus.FIT_AFTER_FONT_REDUCTION,
        FitStatus.FIT_AFTER_BOTH,
    }
)


class TextFitRequest(BaseModel):
    """Everything the fit engine needs to plan how one block/span of
    already-translated text can be rendered — nothing about the
    original PDF is re-derived from this request; the caller supplies
    it from the (immutable) Document Model, per Milestone 2's finding
    that block identity/geometry must come from the planned model, not
    a fresh re-extraction after any mutation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_id: str  # the SourceSpan/Block id this plan targets (Document Model identity, not a re-extracted PyMuPDF index)
    text: str  # translated text to fit — the engine never alters translation semantics, only rendering-safety copies (see numerals.py)
    language: str | None = None  # e.g. "te", "hi", "ta", "kn" — drives the renderer-compatibility fallback, not translation
    script_category: ScriptCategory

    available_rect: PdfRect  # the source geometry to fit into, as extracted (Milestone 2 finding: often tighter than insert_htmlbox needs)
    safety_inset: float = 0.0  # points to shrink available_rect by on every side before use, e.g. to keep clear of a page margin or a neighboring rule/border; 0 = use available_rect exactly as given
    style: TextStyle  # original style, informational/fallback (fit uses initial_font_size as the starting point, not style.font_size, to keep them independently overridable)

    font_family: str  # CSS font-family name declared in the measurement/render CSS
    font_file: str  # path to the font file backing font_family (existence checked -> MISSING_FONT)

    initial_font_size: float
    min_font_size: float
    line_height: float = 1.15
    alignment: str = "left"

    overflow_tolerance: float = 0.0  # points of acceptable overflow beyond available_rect before a fit at min_font_size is still rejected

    allow_horizontal_scaling: bool = False  # forced False by the engine whenever script_category is INDIC, regardless of this value
    allow_geometry_expansion: bool = False
    max_expansion_ratio: float = 0.15  # fraction of the original rect's own width/height it may grow by
    page_bounds: PdfRect | None = None  # any geometry expansion is clamped to this
    obstacle_rects: list[PdfRect] = Field(default_factory=list)  # known neighboring objects; expansion is abandoned entirely if it would touch one (conservative, see engine.py)

    rendering_mode: RenderingMode = RenderingMode.HTMLBOX
    renderer_numeral_fallback: bool = True  # apply the Milestone-2 native-Indic-digit rendering workaround (numerals.py) for languages known to need it

    font_size_step: float = 0.5  # binary search resolution, in points


class GeometryDecision(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_rect: PdfRect
    usable_rect: PdfRect
    expanded: bool = False
    expansion_abandoned_due_to_obstacle: bool = False


class TextFitResult(BaseModel):
    """A deterministic plan: same `TextFitRequest` + same environment
    (fonts, PyMuPDF version) -> same `TextFitResult`. Never mutates the
    source Document Model — the caller applies this plan later via a
    renderer (e.g. `core/pdf/renderer.py`'s `LayoutRenderer`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_id: str
    status: FitStatus
    final_font_size: float | None = None
    final_rect: PdfRect | None = None
    scale: float | None = None  # always 1.0 for a genuine FIT status; the engine controls font size itself rather than relying on insert_htmlbox's own auto-shrink
    spare_height: float | None = None
    line_count_estimate: int | None = None
    overflow: float | None = None  # estimated points of vertical overflow at the final attempted size/rect; populated mainly for NO_FIT diagnostics
    reason: str = ""
    attempted_font_sizes: list[float] = Field(default_factory=list)
    geometry: GeometryDecision | None = None
    native_digit_fallback_applied: bool = False
    rendered_text: str | None = None  # the exact string passed to the renderer for the winning attempt (may differ from `text` only via the numeral fallback)

    @property
    def ok(self) -> bool:
        return self.status in _OK_STATUSES
