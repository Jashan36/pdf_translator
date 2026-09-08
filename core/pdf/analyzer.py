"""PDF Forensics — Phase 1 / Milestone 1 (thin wrapper, Milestone 2+).

"PDF -> inspect -> JSON" (Section 42, Section 69 of the master plan).
As of Milestone 2, the actual extraction logic lives in
`core/pdf/extractor.py` (`PDFExtractor`) — this module keeps only the
native-text-vs-scanned heuristic (Section 15) and a couple of
convenience wrappers used by `app.py`'s forensics view, so PyMuPDF
extraction logic has exactly one implementation, not two.
"""

from __future__ import annotations

import pymupdf

from core.models import Document
from core.pdf.extractor import extract_document


def is_native_text_pdf(doc: pymupdf.Document, sample_pages: int = 3) -> bool:
    """Class A (native text) vs Class B (scanned) heuristic — Section 15.

    Cheap heuristic for Phase 1: if sampled pages contain a meaningful
    amount of extractable text, treat the document as native-text. A
    proper OCR-routing decision belongs to Phase 7 (Section 48); this is
    only a signal surfaced to the user during forensics.
    """
    pages_to_check = min(sample_pages, doc.page_count)
    total_chars = 0
    for i in range(pages_to_check):
        total_chars += len(doc[i].get_text("text").strip())
    return total_chars >= 20 * pages_to_check if pages_to_check else False


def analyze_pdf(path: str) -> Document:
    """Build the internal Document model from a PDF on disk.

    Thin wrapper over `core.pdf.extractor.extract_document` — kept as
    the stable entry point `app.py` uses, in case the forensics view
    ever needs extraction options the plain extractor doesn't expose.
    """
    return extract_document(path)


def analyze_pdf_summary(path: str) -> dict:
    """Convenience wrapper returning a small dict for quick display.

    Full detail lives in analyze_pdf(...).model_dump() — this is just a
    cheap "at a glance" summary (page count, per-page object counts).
    """
    document = analyze_pdf(path)
    return {
        "page_count": document.metadata.page_count,
        "pages": [
            {
                "page": p.page_number,
                "width": round(p.width, 2),
                "height": round(p.height, 2),
                "text_objects": len(p.source_spans),
                "images": len(p.images),
            }
            for p in document.pages
        ],
    }
