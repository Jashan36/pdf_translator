"""Milestone 2: Document Model serialization round-trip tests.

Uses the real golden fixture (via PDFExtractor) rather than a
hand-built minimal document, so this exercises every field the
extractor actually populates, not just a happy-path subset.
"""

from pathlib import Path

from core.pdf.extractor import extract_document
from core.serialization import deserialize_document, load_document, save_document, serialize_document

GOLDEN = Path(__file__).parent / "fixtures" / "golden_multilingual.pdf"


def test_serialize_produces_valid_json_string():
    document = extract_document(str(GOLDEN))
    json_str = serialize_document(document)
    assert isinstance(json_str, str)
    assert json_str.strip().startswith("{")


def test_round_trip_preserves_all_text():
    document = extract_document(str(GOLDEN))
    restored = deserialize_document(serialize_document(document))

    original_texts = [s.text for p in document.pages for s in p.source_spans]
    restored_texts = [s.text for p in restored.pages for s in p.source_spans]
    assert original_texts == restored_texts


def test_round_trip_preserves_geometry_exactly():
    document = extract_document(str(GOLDEN))
    restored = deserialize_document(serialize_document(document))

    for orig_page, restored_page in zip(document.pages, restored.pages):
        assert orig_page.width == restored_page.width
        assert orig_page.height == restored_page.height
        for orig_block, restored_block in zip(orig_page.blocks, restored_page.blocks):
            assert orig_block.bbox == restored_block.bbox


def test_round_trip_preserves_image_and_drawing_metadata():
    document = extract_document(str(GOLDEN))
    restored = deserialize_document(serialize_document(document))

    assert len(restored.pages[0].images) == len(document.pages[0].images)
    assert restored.pages[0].images[0].xref == document.pages[0].images[0].xref
    assert len(restored.pages[0].drawings) == len(document.pages[0].drawings)


def test_save_and_load_document_file_round_trip(tmp_path):
    document = extract_document(str(GOLDEN))
    out_path = tmp_path / "document.json"

    save_document(document, out_path)
    assert out_path.exists()

    restored = load_document(out_path)
    assert restored.page_count == document.page_count
    assert len(restored.pages[0].blocks) == len(document.pages[0].blocks)


def test_serialized_json_has_no_raw_pymupdf_repr():
    document = extract_document(str(GOLDEN))
    json_str = serialize_document(document)
    # A raw pymupdf object's repr would contain its class name — this
    # must never leak into the serialized form (Milestone 2 point 6).
    assert "pymupdf." not in json_str
    assert "<Rect" not in json_str
    assert "<Quad" not in json_str
