"""Milestone 1 regression test: PDF -> internal Document model.

Per Section 42 ("Success criterion"): the extracted model must explain
the original PDF sufficiently to reconstruct a visually similar copy.
This test just checks the forensics layer extracts the geometry/text we
expect from a known fixture — it is not a translation test.
"""

from pathlib import Path

from core.pdf.analyzer import analyze_pdf, is_native_text_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "sample_native.pdf"


def test_analyze_pdf_extracts_page_geometry():
    document = analyze_pdf(str(FIXTURE))

    assert document.metadata.page_count == 1
    page = document.pages[0]
    # A4 in points, per Section 42's example JSON.
    assert round(page.geometry.width, 1) == 595.3
    assert round(page.geometry.height, 1) == 841.9


def test_analyze_pdf_extracts_text_objects_with_bbox_and_font():
    document = analyze_pdf(str(FIXTURE))
    page = document.pages[0]

    texts = [t.original_text for t in page.text_objects]
    assert any("Healthy Food Choices" in t for t in texts)
    assert any("Iron is especially important" in t for t in texts)

    heading = next(t for t in page.text_objects if "Healthy Food Choices" in t.original_text)
    assert heading.font.size > 0
    assert heading.bbox.x1 > heading.bbox.x0
    assert heading.bbox.y1 > heading.bbox.y0


def test_reading_order_is_populated():
    document = analyze_pdf(str(FIXTURE))
    page = document.pages[0]
    assert len(page.reading_order) == len(page.text_objects)
    # reading_order values on text objects should be strictly increasing
    orders = [t.reading_order for t in page.text_objects]
    assert orders == sorted(orders)


def test_native_text_detection():
    import pymupdf as fitz

    with fitz.open(str(FIXTURE)) as doc:
        assert is_native_text_pdf(doc) is True
