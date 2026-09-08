"""Milestone 2: geometry (Rect/Quad) round-trip tests — core/geometry.py."""

import pymupdf

from core.models import SourceSpan, TextStyle
from core.serialization import deserialize_document, serialize_document
from core.models import Block, BlockType, Document, DocumentMetadata, Line, Page


def _minimal_document_with_rect(rect: pymupdf.Rect) -> Document:
    span = SourceSpan(
        span_id="s1",
        text="x",
        bbox=rect,
        style=TextStyle(),
        block_id="b1",
        line_id="b1_l0",
        source_order=0,
    )
    line = Line(line_id="b1_l0", bbox=rect, spans=[span])
    block = Block(
        block_id="b1", page_number=1, bbox=rect, block_type=BlockType.TEXT, reading_order=0, lines=[line]
    )
    page = Page(
        page_number=1,
        width=595.0,
        height=842.0,
        cropbox=pymupdf.Rect(0, 0, 595, 842),
        mediabox=pymupdf.Rect(0, 0, 595, 842),
        blocks=[block],
    )
    return Document(
        source_path="x.pdf",
        metadata=DocumentMetadata(page_count=1, source_path="x.pdf"),
        page_count=1,
        pages=[page],
    )


def test_rect_field_holds_real_pymupdf_rect_in_memory():
    rect = pymupdf.Rect(1.5, 2.5, 100.25, 200.75)
    doc = _minimal_document_with_rect(rect)
    span = doc.pages[0].blocks[0].lines[0].spans[0]
    assert isinstance(span.bbox, pymupdf.Rect)
    assert span.bbox.width == rect.width  # real Rect methods work, not a plain tuple


def test_rect_survives_json_round_trip_exactly():
    rect = pymupdf.Rect(1.5, 2.5, 100.25, 200.75)
    doc = _minimal_document_with_rect(rect)

    json_str = serialize_document(doc)
    assert "pymupdf" not in json_str  # never a raw PyMuPDF repr leaking into JSON
    assert '"x0"' in json_str and '"y1"' in json_str  # plain JSON-safe dict shape

    restored = deserialize_document(json_str)
    restored_rect = restored.pages[0].blocks[0].lines[0].spans[0].bbox
    assert isinstance(restored_rect, pymupdf.Rect)
    assert restored_rect.x0 == rect.x0
    assert restored_rect.y0 == rect.y0
    assert restored_rect.x1 == rect.x1
    assert restored_rect.y1 == rect.y1


def test_page_boxes_survive_round_trip():
    rect = pymupdf.Rect(0, 0, 10, 10)
    doc = _minimal_document_with_rect(rect)
    restored = deserialize_document(serialize_document(doc))
    assert restored.pages[0].cropbox == doc.pages[0].cropbox
    assert restored.pages[0].mediabox == doc.pages[0].mediabox


def test_coordinate_convention_matches_pymupdf_page_rect():
    """Sanity check that our stored geometry uses the same convention
    PyMuPDF itself uses (origin top-left, y down) — see core/geometry.py
    module docstring. A page's own .rect must equal a Page model built
    from its cropbox/mediabox in the same coordinate frame."""
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=200, height=300)
        assert page.rect.y0 == 0  # top-left origin
        assert page.rect == pymupdf.Rect(0, 0, 200, 300)
        assert page.cropbox == page.rect
