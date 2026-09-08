"""core/translation/units.py — TranslationUnit builder tests (point 5)."""

import pymupdf

from core.models import Block, BlockType, Document, DocumentMetadata, Line, Page, SourceSpan, TextStyle
from core.pdf.extractor import extract_document
from core.translation.units import build_units_from_document


def test_units_built_from_real_fixture_one_per_block():
    document = extract_document("tests/fixtures/golden_multilingual.pdf")
    units = build_units_from_document(document, source_language="en")
    text_blocks = [b for b in document.pages[0].blocks if b.block_type == BlockType.TEXT]
    assert len(units) == len(text_blocks)
    for unit in units:
        assert unit.text.strip()
        assert unit.span_ids


def _multi_span_document() -> Document:
    """"Total" + "₹" + "1500" as three separately-styled spans within
    ONE block/line -- the exact non-fragmentation example from point 5."""
    spans = [
        SourceSpan(
            span_id=f"s{i}", text=text, bbox=pymupdf.Rect(x, 0, x + 20, 10),
            style=TextStyle(), block_id="b1", line_id="b1_l0", source_order=i,
        )
        for i, (text, x) in enumerate([("Total ", 0), ("₹", 20), ("1500", 25)])
    ]
    line = Line(line_id="b1_l0", bbox=pymupdf.Rect(0, 0, 45, 10), spans=spans)
    block = Block(
        block_id="b1", page_number=1, bbox=pymupdf.Rect(0, 0, 45, 10),
        block_type=BlockType.TEXT, reading_order=0, lines=[line], raw_text="Total ₹1500",
    )
    page = Page(
        page_number=1, width=200, height=200,
        cropbox=pymupdf.Rect(0, 0, 200, 200), mediabox=pymupdf.Rect(0, 0, 200, 200), blocks=[block],
    )
    return Document(
        source_path="x.pdf", metadata=DocumentMetadata(page_count=1, source_path="x.pdf"),
        page_count=1, pages=[page],
    )


def test_multi_span_line_becomes_one_unit_not_three():
    document = _multi_span_document()
    units = build_units_from_document(document, source_language="en")
    assert len(units) == 1
    assert units[0].text == "Total ₹1500"
    assert units[0].span_ids == ["s0", "s1", "s2"]


def test_unit_bbox_is_union_of_member_spans():
    document = _multi_span_document()
    units = build_units_from_document(document, source_language="en")
    unit = units[0]
    assert unit.bbox.x0 == 0
    assert unit.bbox.x1 == 45  # union reaches the rightmost span's edge


def test_unit_id_matches_first_span_for_pipeline_compatibility():
    document = _multi_span_document()
    units = build_units_from_document(document, source_language="en")
    assert units[0].unit_id == "s0"


def test_empty_blocks_produce_no_units():
    block = Block(
        block_id="empty", page_number=1, bbox=pymupdf.Rect(0, 0, 10, 10),
        block_type=BlockType.TEXT, reading_order=0, lines=[], raw_text="",
    )
    page = Page(
        page_number=1, width=200, height=200,
        cropbox=pymupdf.Rect(0, 0, 200, 200), mediabox=pymupdf.Rect(0, 0, 200, 200), blocks=[block],
    )
    document = Document(
        source_path="x.pdf", metadata=DocumentMetadata(page_count=1, source_path="x.pdf"),
        page_count=1, pages=[page],
    )
    assert build_units_from_document(document, source_language="en") == []
