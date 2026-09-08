"""Milestone 2: Document Model unit tests.

Covers construction of every model type and the immutability /
source-vs-translated separation the model's docstring requires — see
`core/models.py`.
"""

import pymupdf
import pytest
from pydantic import ValidationError

from core.models import (
    Block,
    BlockType,
    Document,
    DocumentMetadata,
    Drawing,
    Image,
    Line,
    Page,
    SourceSpan,
    TextStyle,
    Table,
    TranslatedSpan,
    TranslationStatus,
)


def make_source_span(span_id="s1", text="Hello world") -> SourceSpan:
    return SourceSpan(
        span_id=span_id,
        text=text,
        bbox=pymupdf.Rect(10, 20, 100, 40),
        style=TextStyle(font_name="Helvetica", font_size=12.0),
        block_id="b1",
        line_id="b1_l0",
        source_order=0,
    )


def test_source_span_holds_real_pymupdf_rect():
    span = make_source_span()
    assert isinstance(span.bbox, pymupdf.Rect)
    assert span.bbox.width == 90
    assert span.bbox.height == 20


def test_source_span_is_immutable():
    span = make_source_span()
    with pytest.raises(ValidationError):
        span.text = "tampered"


def test_translated_span_never_mutates_source():
    source = make_source_span(text="Hello world")
    translated = TranslatedSpan(
        source_span_id=source.span_id,
        text="Hola mundo",
        style=source.style,
        status=TranslationStatus.TRANSLATED,
    )
    # Source is untouched; translation is a distinct, linked object.
    assert source.text == "Hello world"
    assert translated.text == "Hola mundo"
    assert translated.source_span_id == source.span_id
    assert translated is not source


def test_translated_span_can_reuse_or_override_bbox():
    source = make_source_span()
    same_box = TranslatedSpan(source_span_id=source.span_id, text="x", style=source.style)
    assert same_box.bbox is None  # caller falls back to source.bbox

    new_box = TranslatedSpan(
        source_span_id=source.span_id, text="x", style=source.style, bbox=pymupdf.Rect(0, 0, 50, 50)
    )
    assert isinstance(new_box.bbox, pymupdf.Rect)


def test_line_block_page_document_nest_correctly():
    span = make_source_span()
    line = Line(line_id="b1_l0", bbox=pymupdf.Rect(10, 20, 100, 40), spans=[span])
    block = Block(
        block_id="b1",
        page_number=1,
        bbox=pymupdf.Rect(10, 20, 100, 40),
        block_type=BlockType.TEXT,
        reading_order=0,
        lines=[line],
        raw_text="Hello world",
    )
    page = Page(
        page_number=1,
        width=595.0,
        height=842.0,
        cropbox=pymupdf.Rect(0, 0, 595, 842),
        mediabox=pymupdf.Rect(0, 0, 595, 842),
        blocks=[block],
        reading_order=["b1"],
    )
    document = Document(
        source_path="test.pdf",
        metadata=DocumentMetadata(page_count=1, source_path="test.pdf"),
        page_count=1,
        pages=[page],
    )

    assert document.pages[0].blocks[0].lines[0].spans[0].text == "Hello world"
    assert document.pages[0].source_spans == [span]


def test_image_drawing_table_construct():
    image = Image(image_id="i1", page_number=1, bbox=pymupdf.Rect(0, 0, 10, 10), xref=5)
    drawing = Drawing(drawing_id="d1", page_number=1, bbox=pymupdf.Rect(0, 0, 10, 10), kind="fs")
    table = Table(table_id="t1", page_number=1, bbox=pymupdf.Rect(0, 0, 100, 100))

    assert image.xref == 5
    assert drawing.kind == "fs"
    assert table.rows == 0 and table.cells == []  # placeholder structure, not yet populated


def test_text_style_defaults_are_optional_not_guessed():
    style = TextStyle()
    assert style.alignment is None  # not guessed when unknown
    assert style.char_flags is None
