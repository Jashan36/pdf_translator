"""Serialization / deserialization for the Document Model.

Per Milestone 2 instructions: JSON-compatible structures only — never
serialize a raw PyMuPDF object. `core/geometry.py`'s `PdfRect`/`PdfQuad`
annotated types already teach pydantic how to turn a `pymupdf.Rect`/
`Quad` into a plain JSON-safe dict and back, so `Document.model_dump_json()`
/ `Document.model_validate_json()` already do the right thing on their
own — these functions exist as the single documented, testable place
that behavior is exercised, useful for debugging, testing, research,
and future caching (per the Milestone 2 spec) without every caller
needing to know pydantic is involved.
"""

from __future__ import annotations

from pathlib import Path

from core.models import Document


def serialize_document(document: Document) -> str:
    """Document -> JSON string. No raw PyMuPDF object is ever touched:
    `Rect`/`Quad` fields serialize via the `PdfRect`/`PdfQuad` types."""
    return document.model_dump_json(indent=2)


def deserialize_document(data: str) -> Document:
    """JSON string -> Document, with `Rect`/`Quad` fields reconstructed
    as real `pymupdf.Rect`/`Quad` objects (not left as plain dicts)."""
    return Document.model_validate_json(data)


def save_document(document: Document, path: str | Path) -> None:
    Path(path).write_text(serialize_document(document), encoding="utf-8")


def load_document(path: str | Path) -> Document:
    return deserialize_document(Path(path).read_text(encoding="utf-8"))
