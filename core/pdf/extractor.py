"""PDFExtractor — the one place PyMuPDF-specific extraction logic lives.

Per Milestone 2 instructions: "Do not put PyMuPDF-specific logic
throughout the application." Everything else in this project (the
Streamlit app, the layout engine, translation, QA) talks to the
Document Model (`core/models.py`), never to `pymupdf` objects directly
for extraction purposes. Only this module and `core/pdf/analyzer.py`'s
thin forensics wrapper import `pymupdf` for reading a source PDF.

See the `pdf-forensics` skill before changing this file.
"""

from __future__ import annotations

import math
import os

import pymupdf

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
)

# PyMuPDF span "flags" bitmask (see textpage docs referenced in the
# pdf-forensics skill and docs/research/pymupdf.md).
_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4


def _style_from_span(span: dict) -> TextStyle:
    flags = span.get("flags", 0)
    font_name = span.get("font", "unknown")
    return TextStyle(
        font_name=font_name,
        font_size=float(span.get("size", 0.0)),
        color=int(span.get("color", 0)),
        bold=bool(flags & _FLAG_BOLD) or "bold" in font_name.lower(),
        italic=bool(flags & _FLAG_ITALIC) or "italic" in font_name.lower(),
        opacity=float(span.get("alpha", 255)) / 255.0 if "alpha" in span else 1.0,
        flags=flags,
        char_flags=span.get("char_flags"),
    )


def _line_rotation_degrees(direction: tuple[float, float]) -> float:
    dir_x, dir_y = direction
    return round(-math.degrees(math.atan2(dir_y, dir_x)), 2)


class PDFExtractor:
    """Extraction adapter: PDF path -> `Document` model.

    This is the ONLY supported way to build a `Document` from a PDF
    file in this codebase. Do not re-implement span/block extraction
    elsewhere — extend this class instead.
    """

    def extract_document(self, path: str) -> Document:
        pdf = pymupdf.open(path)
        try:
            return self._build_document(pdf, path)
        finally:
            pdf.close()

    # -- internals -----------------------------------------------------

    def _build_document(self, pdf: pymupdf.Document, path: str) -> Document:
        meta = pdf.metadata or {}
        document = Document(
            source_path=os.path.basename(path),
            metadata=DocumentMetadata(
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                creator=meta.get("creator") or None,
                producer=meta.get("producer") or None,
                creation_date=meta.get("creationDate") or None,
                modification_date=meta.get("modDate") or None,
                page_count=pdf.page_count,
                source_path=os.path.basename(path),
            ),
            page_count=pdf.page_count,
        )

        for page_index in range(pdf.page_count):
            document.pages.append(self._build_page(pdf[page_index], page_index + 1))

        return document

    def _build_page(self, pdf_page: pymupdf.Page, page_number: int) -> Page:
        page = Page(
            page_number=page_number,
            width=pdf_page.rect.width,
            height=pdf_page.rect.height,
            rotation=pdf_page.rotation,
            cropbox=pdf_page.cropbox,
            mediabox=pdf_page.mediabox,
        )

        text_dict = pdf_page.get_text("dict")
        source_order = 0
        for raw_block in text_dict.get("blocks", []):
            block, source_order = self._build_block(raw_block, page_number, source_order)
            page.blocks.append(block)

        page.reading_order = [b.block_id for b in sorted(page.blocks, key=lambda b: b.reading_order)]

        page.images = self._build_images(pdf_page, page_number)
        page.drawings = self._build_drawings(pdf_page, page_number)

        return page

    def _build_block(
        self, raw_block: dict, page_number: int, source_order: int
    ) -> tuple[Block, int]:
        block_id = f"p{page_number}_b{raw_block.get('number', 0)}"
        raw_type = raw_block.get("type", 0)
        block_type = BlockType.TEXT if raw_type == 0 else (
            BlockType.IMAGE if raw_type == 1 else BlockType.UNKNOWN
        )
        bbox = raw_block.get("bbox", (0, 0, 0, 0))

        block = Block(
            block_id=block_id,
            page_number=page_number,
            bbox=bbox,
            block_type=block_type,
            reading_order=raw_block.get("number", 0),
        )

        raw_text_parts: list[str] = []
        for line_idx, raw_line in enumerate(raw_block.get("lines", [])):
            line_id = f"{block_id}_l{line_idx}"
            direction = tuple(raw_line.get("dir", (1.0, 0.0)))
            line = Line(
                line_id=line_id,
                bbox=raw_line.get("bbox", (0, 0, 0, 0)),
                direction=direction,
            )

            for span_idx, raw_span in enumerate(raw_line.get("spans", [])):
                text = raw_span.get("text", "")
                if not text.strip():
                    continue
                span_id = f"{line_id}_s{span_idx}"
                origin = raw_span.get("origin")
                span = SourceSpan(
                    span_id=span_id,
                    text=text,
                    bbox=raw_span.get("bbox", (0, 0, 0, 0)),
                    style=_style_from_span(raw_span),
                    block_id=block_id,
                    line_id=line_id,
                    source_order=source_order,
                    origin=tuple(origin) if origin else None,
                    ascender=raw_span.get("ascender"),
                    descender=raw_span.get("descender"),
                    alpha=raw_span.get("alpha", 255) / 255.0 if "alpha" in raw_span else None,
                    rotation=_line_rotation_degrees(direction),
                )
                line.spans.append(span)
                raw_text_parts.append(text)
                source_order += 1

            if line.spans:
                if line.spans[0].origin:
                    line.baseline_y = line.spans[0].origin[1]
                block.lines.append(line)

        block.raw_text = "".join(raw_text_parts)
        return block, source_order

    def _build_images(self, pdf_page: pymupdf.Page, page_number: int) -> list[Image]:
        images: list[Image] = []
        for img_idx, img in enumerate(pdf_page.get_images(full=True)):
            xref = img[0]
            width, height = img[2], img[3]
            colorspace_n = img[5] if len(img) > 5 else None
            rects = pdf_page.get_image_rects(xref)
            for rect_idx, rect in enumerate(rects or [pdf_page.rect]):
                images.append(
                    Image(
                        image_id=f"p{page_number}_img{img_idx}_{rect_idx}",
                        page_number=page_number,
                        bbox=rect,
                        xref=xref,
                        width=width or None,
                        height=height or None,
                        colorspace=str(colorspace_n) if colorspace_n else None,
                    )
                )
        return images

    def _build_drawings(self, pdf_page: pymupdf.Page, page_number: int) -> list[Drawing]:
        drawings: list[Drawing] = []
        for idx, d in enumerate(pdf_page.get_drawings()):
            drawings.append(
                Drawing(
                    drawing_id=f"p{page_number}_d{idx}",
                    page_number=page_number,
                    bbox=d.get("rect", pdf_page.rect),
                    kind=d.get("type", "unknown"),
                    stroke_color=tuple(d["color"]) if d.get("color") else None,
                    fill_color=tuple(d["fill"]) if d.get("fill") else None,
                    width=d.get("width"),
                    stroke_opacity=d.get("stroke_opacity"),
                    fill_opacity=d.get("fill_opacity"),
                )
            )
        return drawings


def extract_document(path: str) -> Document:
    """Module-level convenience wrapper around `PDFExtractor`."""
    return PDFExtractor().extract_document(path)
