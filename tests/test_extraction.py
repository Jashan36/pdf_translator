"""Extraction tests: Milestone 1 (sample_native.pdf) + Milestone 2
(golden_multilingual.pdf) — core/pdf/extractor.py's PDFExtractor.

Per Milestone 2 point 7: page count, page dimensions, block count,
text presence, bounding boxes, font metadata, image detection, and
reading order. Translation is explicitly out of scope here.
"""

from pathlib import Path

import pymupdf

from core.pdf.analyzer import is_native_text_pdf
from core.pdf.extractor import extract_document

FIXTURE = Path(__file__).parent / "fixtures" / "sample_native.pdf"
GOLDEN = Path(__file__).parent / "fixtures" / "golden_multilingual.pdf"


# --- Milestone 1 fixture (kept as a smoke test against the new extractor) ---


def test_analyze_pdf_extracts_page_geometry():
    document = extract_document(str(FIXTURE))

    assert document.metadata.page_count == 1
    page = document.pages[0]
    assert round(page.width, 1) == 595.3
    assert round(page.height, 1) == 841.9


def test_analyze_pdf_extracts_text_objects_with_bbox_and_font():
    document = extract_document(str(FIXTURE))
    page = document.pages[0]

    texts = [t.text for t in page.source_spans]
    assert any("Healthy Food Choices" in t for t in texts)
    assert any("Iron is especially important" in t for t in texts)

    heading = next(t for t in page.source_spans if "Healthy Food Choices" in t.text)
    assert heading.style.font_size > 0
    assert heading.bbox.x1 > heading.bbox.x0
    assert heading.bbox.y1 > heading.bbox.y0


def test_native_text_detection():
    with pymupdf.open(str(FIXTURE)) as doc:
        assert is_native_text_pdf(doc) is True


# --- Milestone 2 golden fixture ---------------------------------------


def test_golden_page_count_and_dimensions():
    document = extract_document(str(GOLDEN))
    assert document.page_count == 1
    page = document.pages[0]
    assert round(page.width, 2) == 595.28
    assert round(page.height, 2) == 841.89
    assert page.cropbox == page.mediabox  # no separate crop applied by the fixture builder


def test_golden_block_count():
    document = extract_document(str(GOLDEN))
    page = document.pages[0]
    # heading, 2 English paragraphs, 4 Indic sentences, 1 mixed sentence, 1 image block = 9
    assert len(page.blocks) == 9


def test_golden_text_presence_all_scripts():
    document = extract_document(str(GOLDEN))
    all_text = "".join(b.raw_text for b in document.pages[0].blocks)

    assert "Multilingual Test Document" in all_text
    assert "This document exercises extraction" in all_text
    assert "ఇది ఒక పరీక్ష వాక్యం." in all_text  # Telugu
    assert "यह एक परीक्षण वाक्य है।" in all_text  # Hindi
    assert "இது ஒரு சோதனை வாக்கியம்." in all_text  # Tamil
    assert "ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯ." in all_text  # Kannada
    assert "COVID-19" in all_text and "మహమ్మారి" in all_text  # mixed script


def test_golden_bounding_boxes_are_nonzero_and_ordered():
    document = extract_document(str(GOLDEN))
    for block in document.pages[0].blocks:
        assert block.bbox.x1 > block.bbox.x0
        assert block.bbox.y1 > block.bbox.y0
        for line in block.lines:
            for span in line.spans:
                assert span.bbox.x1 > span.bbox.x0
                assert span.bbox.y1 > span.bbox.y0


def test_golden_font_metadata_present_where_available():
    document = extract_document(str(GOLDEN))
    spans = document.pages[0].source_spans
    assert spans, "expected at least one extracted span"
    for span in spans:
        assert span.style.font_size > 0
        assert span.style.font_name != ""


def test_golden_image_detection():
    document = extract_document(str(GOLDEN))
    page = document.pages[0]
    assert len(page.images) == 1
    image = page.images[0]
    assert image.width == 64 and image.height == 64
    assert image.xref is not None


def test_golden_drawing_detection():
    document = extract_document(str(GOLDEN))
    page = document.pages[0]
    assert len(page.drawings) == 1
    assert page.drawings[0].fill_color is not None


def test_golden_reading_order_matches_vertical_layout():
    document = extract_document(str(GOLDEN))
    page = document.pages[0]

    # Blocks were placed top-to-bottom in the fixture builder, so
    # reading order should follow the same top-to-bottom sequence.
    ordered_blocks = [b for b in page.blocks if b.block_id in page.reading_order]
    ordered_blocks.sort(key=lambda b: page.reading_order.index(b.block_id))
    y_positions = [b.bbox.y0 for b in ordered_blocks]
    assert y_positions == sorted(y_positions)
