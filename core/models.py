"""Internal Document Model — Milestone 2.

The normalized representation that carries a PDF through:

    extraction -> semantic transformation -> translation
    -> layout fitting -> rendering

without losing original geometry or styling. See
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 4 and master plan
Section 5 for the design rationale, and `core/geometry.py` for the
coordinate convention every `bbox`/`quad` field here follows.

Key structural decisions (Milestone 2):

- The extracted source tree (`SourceSpan` etc.) is immutable
  (`model_config = ConfigDict(frozen=True)`) — nothing downstream may
  overwrite `SourceSpan.text`. A translation is a *separate* object
  (`TranslatedSpan`) linked back to its source by id, never a mutation.
- `Block`/`Line`/`Span` mirror PyMuPDF's own extraction hierarchy
  (`get_text("dict")`: blocks -> lines -> spans) rather than inventing
  a different shape, so nothing from the source extraction is
  silently discarded when building this model.
- Geometry (`bbox`, `Quad`) is kept as real `pymupdf.Rect`/`Quad`
  objects in memory (see `core/geometry.py`), not flattened to plain
  tuples prematurely — but is still fully JSON-serializable via the
  `PdfRect`/`PdfQuad` annotated types, so `core/serialization.py` never
  needs to touch a raw PyMuPDF object.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from core.geometry import PdfQuad, PdfRect


class TranslationStatus(str, Enum):
    PENDING = "pending"
    TRANSLATED = "translated"
    SKIPPED = "skipped"
    FAILED = "failed"


class BlockType(str, Enum):
    """Matches PyMuPDF's raw `get_text("dict")` block `type` field
    (0 = text, 1 = image), plus UNKNOWN for anything else encountered."""

    TEXT = "text"
    IMAGE = "image"
    UNKNOWN = "unknown"


# --- Style -------------------------------------------------------------


class TextStyle(BaseModel):
    """Reusable style structure. Not every PDF exposes every property —
    fields the source extraction couldn't determine stay `None` rather
    than being guessed (CLAUDE.md's stop rule: a warning/None beats an
    invented value)."""

    font_name: str = "unknown"
    font_size: float = 0.0
    color: int = 0  # packed sRGB int, as PyMuPDF returns it
    bold: bool = False
    italic: bool = False
    alignment: str | None = None  # not exposed by raw span extraction; set later by layout analysis
    opacity: float = 1.0
    flags: int = 0  # raw PyMuPDF span flags — kept for reference; see pdf-forensics skill's warning that flags can be wrong
    char_flags: int | None = None  # PyMuPDF's finer-grained per-char flags, when available


# --- Span ----------------------------------------------------------------


class SourceSpan(BaseModel):
    """One immutable span exactly as extracted from the source PDF.

    Never construct a `SourceSpan` with translated content, and never
    mutate `.text` after creation — see module docstring. A
    translation is a separate `TranslatedSpan` linked by `span_id`.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    span_id: str
    text: str
    bbox: PdfRect
    style: TextStyle
    block_id: str
    line_id: str
    source_order: int  # position of this span within the overall extraction sequence
    origin: tuple[float, float] | None = None  # baseline origin point, per PyMuPDF span "origin"
    ascender: float | None = None  # ratio, per PyMuPDF span "ascender"
    descender: float | None = None  # ratio, per PyMuPDF span "descender"
    alpha: float | None = None  # 0-1 opacity, when PyMuPDF reports it distinctly from style.opacity
    rotation: float = 0.0


class TranslatedSpan(BaseModel):
    """A translation of one `SourceSpan`. Always linked back to its
    source by id — never replaces or mutates the `SourceSpan` itself."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_span_id: str
    text: str
    style: TextStyle  # may differ from the source style (e.g. substituted Indic font)
    bbox: PdfRect | None = None  # target bbox, if different from the source span's; None = reuse source bbox
    status: TranslationStatus = TranslationStatus.PENDING
    confidence: float = 1.0


# --- Line / Block ----------------------------------------------------------


class Line(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    line_id: str
    bbox: PdfRect
    spans: list[SourceSpan] = Field(default_factory=list)
    baseline_y: float | None = None  # approximated from the first span's origin, when available
    direction: tuple[float, float] | None = None  # PyMuPDF line "dir" vector; (1,0) is upright horizontal


class Block(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    block_id: str
    page_number: int
    bbox: PdfRect
    block_type: BlockType
    reading_order: int
    lines: list[Line] = Field(default_factory=list)
    raw_text: str = ""  # concatenation of the block's own extracted text, before any grouping/translation


# --- Image / Drawing / Table ------------------------------------------------


class Image(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    image_id: str
    page_number: int
    bbox: PdfRect
    xref: int | None = None  # PyMuPDF internal image reference, for lossless copy
    width: int | None = None
    height: int | None = None
    colorspace: str | None = None


class Drawing(BaseModel):
    """A vector graphic (PyMuPDF `page.get_drawings()` entry)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    drawing_id: str
    page_number: int
    bbox: PdfRect
    kind: str = "unknown"  # PyMuPDF drawing "type", e.g. "f" (fill), "s" (stroke), "fs" (both)
    stroke_color: tuple[float, float, float] | None = None
    fill_color: tuple[float, float, float] | None = None
    width: float | None = None
    stroke_opacity: float | None = None
    fill_opacity: float | None = None


class TableCell(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    row: int
    col: int
    bbox: PdfRect | None = None
    text: str = ""


class Table(BaseModel):
    """Placeholder structure — table extraction is not implemented yet
    (master plan Phase 8 / Section 25). Kept here so the Document Model
    already has a stable shape to grow into, per Section 5's design;
    `rows`/`cols`/`cells` stay empty until that milestone."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    table_id: str
    page_number: int
    bbox: PdfRect
    rows: int = 0
    cols: int = 0
    cells: list[TableCell] = Field(default_factory=list)


# --- Page / Document ---------------------------------------------------


class Page(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page_number: int
    width: float
    height: float
    rotation: int = 0
    cropbox: PdfRect
    mediabox: PdfRect
    blocks: list[Block] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    drawings: list[Drawing] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    reading_order: list[str] = Field(default_factory=list)  # block_ids, in reading order

    @property
    def source_spans(self) -> list[SourceSpan]:
        """All source spans on this page, in extraction order, across
        every block/line. Convenience accessor — the canonical storage
        remains the nested block/line structure."""
        return [span for block in self.blocks for line in block.lines for span in line.spans]


class DocumentMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    page_count: int = 0
    source_path: str | None = None


class Document(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_path: str
    metadata: DocumentMetadata
    page_count: int
    pages: list[Page] = Field(default_factory=list)
    source_language: str | None = None
    target_language: str | None = None
    glossary: dict[str, str] = Field(default_factory=dict)
    translation_memory: dict[str, str] = Field(default_factory=dict)
    qa_results: dict = Field(default_factory=dict)
