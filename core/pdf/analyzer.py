"""PDF Forensics — Phase 1 / Milestone 1.

"PDF -> inspect -> JSON" (Section 42, Section 69). No translation, no
rendering here — this module only *reads* a PDF and builds the internal
Document model (core/models.py) using PyMuPDF span/bbox/font metadata.

Success criterion (Section 42): the extracted model must explain the
original PDF sufficiently to reconstruct a visually similar copy later.
"""

from __future__ import annotations

import math
import os

import pymupdf as fitz

from core.models import (
    BBox,
    Document,
    DocumentMetadata,
    FontInfo,
    ImageObject,
    Page,
    PageGeometry,
    TextObject,
)

# PyMuPDF span "flags" bitmask (see textpage docs referenced in the plan).
_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4


def _font_from_span(span: dict) -> FontInfo:
    flags = span.get("flags", 0)
    return FontInfo(
        name=span.get("font", "unknown"),
        size=float(span.get("size", 0.0)),
        flags=flags,
        bold=bool(flags & _FLAG_BOLD) or "bold" in span.get("font", "").lower(),
        italic=bool(flags & _FLAG_ITALIC) or "italic" in span.get("font", "").lower(),
        color=int(span.get("color", 0)),
        opacity=float(span.get("alpha", 255)) / 255.0 if "alpha" in span else 1.0,
    )


def is_native_text_pdf(doc: fitz.Document, sample_pages: int = 3) -> bool:
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

    This is the single entry point for Phase 1. It does not translate,
    does not modify the file, and does not render anything — it only
    extracts geometry, style and structure per Section 5 / 17 / 18.
    """
    doc = fitz.open(path)
    try:
        meta = doc.metadata or {}
        document = Document(
            metadata=DocumentMetadata(
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                creator=meta.get("creator") or None,
                producer=meta.get("producer") or None,
                creation_date=meta.get("creationDate") or None,
                modification_date=meta.get("modDate") or None,
                page_count=doc.page_count,
                source_path=os.path.basename(path),
            )
        )

        for page_index in range(doc.page_count):
            page = doc[page_index]
            page_number = page_index + 1

            page_model = Page(
                page_number=page_number,
                geometry=PageGeometry(
                    width=page.rect.width,
                    height=page.rect.height,
                    rotation=page.rotation,
                ),
            )

            # --- Text extraction (blocks -> lines -> spans) ---
            reading_order_counter = 0
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue  # not a text block (images handled below)
                block_id = f"p{page_number}_b{block.get('number', 0)}"
                for line_idx, line in enumerate(block.get("lines", [])):
                    dir_x, dir_y = line.get("dir", (1.0, 0.0))
                    # Text direction vector -> degrees, for rotated text (Section 21).
                    line_rotation = -math.degrees(math.atan2(dir_y, dir_x))
                    for span_idx, span in enumerate(line.get("spans", [])):
                        text = span.get("text", "")
                        if not text.strip():
                            continue
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        obj_id = f"{block_id}_l{line_idx}_s{span_idx}"
                        text_obj = TextObject(
                            id=obj_id,
                            page_number=page_number,
                            reading_order=reading_order_counter,
                            original_text=text,
                            bbox=BBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                            font=_font_from_span(span),
                            rotation=round(line_rotation, 2),
                            parent_block=block_id,
                        )
                        page_model.text_objects.append(text_obj)
                        page_model.reading_order.append(obj_id)
                        reading_order_counter += 1

            # --- Images ---
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                rects = page.get_image_rects(xref)
                for rect_idx, rect in enumerate(rects or [page.rect]):
                    image_obj = ImageObject(
                        id=f"p{page_number}_img{img_idx}_{rect_idx}",
                        page_number=page_number,
                        bbox=BBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
                        xref=xref,
                    )
                    page_model.images.append(image_obj)

            document.pages.append(page_model)

        return document
    finally:
        doc.close()


def analyze_pdf_summary(path: str) -> dict:
    """Convenience wrapper returning a small dict for quick UI display.

    Full detail lives in analyze_pdf(...).model_dump() — this is just a
    cheap "at a glance" summary (page count, per-page object counts).
    """
    document = analyze_pdf(path)
    return {
        "page_count": document.metadata.page_count,
        "pages": [
            {
                "page": p.page_number,
                "width": round(p.geometry.width, 2),
                "height": round(p.geometry.height, 2),
                "text_objects": len(p.text_objects),
                "images": len(p.images),
            }
            for p in document.pages
        ],
    }
