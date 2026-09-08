"""Internal document model.

This is the representation the rest of the pipeline (translation, layout,
rendering, QA) operates on. It is built once from the raw PDF (see
``core/pdf/analyzer.py``) and never mutated by an LLM directly — only
deterministic code writes bbox/geometry fields, and only the translation
layer writes ``translated_text``.

See: "5. Document Understanding Layer" and "18. Bounding Box Model" in
local_pdf_localizer_technical_master_plan.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ObjectType(str, Enum):
    """Section 17 — object classification."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VECTOR = "VECTOR"
    TABLE = "TABLE"
    FORM = "FORM"
    ANNOTATION = "ANNOTATION"
    UNKNOWN = "UNKNOWN"


class TranslationStatus(str, Enum):
    PENDING = "pending"
    TRANSLATED = "translated"
    SKIPPED = "skipped"
    FAILED = "failed"


class BBox(BaseModel):
    """Section 18 — Bounding Box Model."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


class FontInfo(BaseModel):
    """Section 21 — Style Preservation."""

    name: str = "unknown"
    size: float = 0.0
    flags: int = 0
    bold: bool = False
    italic: bool = False
    color: int = 0  # sRGB packed int, as returned by PyMuPDF
    opacity: float = 1.0


class TextObject(BaseModel):
    """A single semantic/rendering text unit.

    Field list matches Section 5 exactly (with Python-friendly names).
    """

    id: str
    page_number: int
    reading_order: int
    original_text: str
    translated_text: str | None = None
    bbox: BBox
    font: FontInfo
    rotation: float = 0.0
    alignment: str | None = None
    line_height: float | None = None
    role: str | None = None  # e.g. "heading", "paragraph", "caption", "header", "footer"
    parent_block: str | None = None
    section: str | None = None
    confidence: float = 1.0
    translation_status: TranslationStatus = TranslationStatus.PENDING


class ImageObject(BaseModel):
    id: str
    page_number: int
    bbox: BBox
    xref: int | None = None  # PyMuPDF internal image reference, for lossless copy


class VectorObject(BaseModel):
    id: str
    page_number: int
    bbox: BBox
    kind: str = "unknown"  # e.g. "line", "rect", "path"


class PageGeometry(BaseModel):
    width: float
    height: float
    rotation: int = 0


class Page(BaseModel):
    page_number: int
    geometry: PageGeometry
    background: str | None = None
    text_objects: list[TextObject] = Field(default_factory=list)
    images: list[ImageObject] = Field(default_factory=list)
    vectors: list[VectorObject] = Field(default_factory=list)
    reading_order: list[str] = Field(default_factory=list)  # TextObject ids, in order


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
    """Top-level internal document model (Section 5)."""

    metadata: DocumentMetadata
    source_language: str | None = None
    target_language: str | None = None
    pages: list[Page] = Field(default_factory=list)
    glossary: dict[str, str] = Field(default_factory=dict)
    translation_memory: dict[str, str] = Field(default_factory=dict)
    qa_results: dict = Field(default_factory=dict)
