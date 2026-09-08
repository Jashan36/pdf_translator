"""Single-block redact/reinsert proof (Milestone 2, point 9).

Deliberately narrow: prove that ONE source text block can be
identified, isolated, safely redacted, and correctly reinserted with
`insert_htmlbox` — before any whole-document replacement pipeline is
built. Per `docs/research/pymupdf.md`: there is no built-in "replace
this span" API in PyMuPDF; the documented/community-confirmed pattern
is redact (which actually deletes the underlying content-stream
operators) then reinsert in a second pass. This module implements
exactly that pattern, tightly scoped to a single span's bbox so
neighboring objects are not collaterally affected.
"""

from __future__ import annotations

import pymupdf
from pydantic import BaseModel, ConfigDict

from core.geometry import PdfRect
from core.models import SourceSpan, TextStyle, TranslatedSpan, TranslationStatus
from core.pdf.renderer import LayoutRenderer, RenderResult


class RedactReinsertResult(BaseModel):
    """Everything needed to verify the proof succeeded: the render
    outcome plus enough state to compare against original geometry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    render_result: RenderResult
    redacted_bbox: PdfRect
    original_text: str
    new_text: str


def redact_and_reinsert_span(
    page: pymupdf.Page,
    span: SourceSpan,
    translated_text: str,
    *,
    font_family: str,
    font_filename: str,
    font_archive: pymupdf.Archive,
    font_size: float | None = None,
    scale_low: float = 0.3,
) -> RedactReinsertResult:
    """Replace exactly `span`'s content on `page`, leaving everything
    else on the page untouched.

    Steps (per the pymupdf.md research and master plan Section 43):
      1. identify  -> `span` (already located via `PDFExtractor`)
      2. isolate   -> `span.bbox`, scoped tightly (no padding beyond
                      the span's own rect, so neighboring text/images
                      on the same line are not swept into the redaction)
      3. cover/redact safely -> `add_redact_annot` + `apply_redactions`
                      restricted to graphics/images OFF, so only the
                      text content stream operators in that exact
                      rectangle are removed
      4. reinsert  -> `insert_htmlbox` (never the classic text APIs,
                      per Decision 7 / the rendering proof)
      5. render    -> handled by the caller via `page.get_pixmap()`
      6. compare   -> the caller re-extracts the page and diffs
                      geometry of everything else (see
                      tests/test_redaction_reinsertion.py)
    """
    bbox = span.bbox  # pymupdf.Rect, per core/geometry.py's convention

    # Step 3: redact, scoped to exactly this span's rect. images=False,
    # graphics=False so this cannot collaterally strip nearby vector
    # art or images even if the rect were slightly mis-scoped.
    page.add_redact_annot(bbox)
    page.apply_redactions(
        images=pymupdf.PDF_REDACT_IMAGE_NONE,
        graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
    )

    # Step 4: reinsert via the shared LayoutRenderer (insert_htmlbox only).
    size = font_size or span.style.font_size or 12.0
    css = (
        f"@font-face {{font-family: {font_family}; src: url({font_filename});}}\n"
        f"* {{font-family: {font_family}; font-size: {size}px;}}"
    )
    translated = TranslatedSpan(
        source_span_id=span.span_id,
        text=translated_text,
        style=TextStyle(font_name=font_family, font_size=size),
        status=TranslationStatus.TRANSLATED,
    )
    renderer = LayoutRenderer(font_archive=font_archive)
    # scale_low < 1.0: the extracted span bbox is tight to the source
    # text's glyph-ink extents (see core/pdf/extractor.py), which is
    # usually smaller than insert_htmlbox's own line-box model for the
    # SAME text at the SAME font size, let alone a translated string of
    # different length. Calibrating this precisely is Milestone 3's
    # job (the automatic text-fit engine) -- this proof only needs to
    # show the redact->reinsert mechanism itself works, so a modest
    # amount of allowed shrinkage keeps the proof from failing on a
    # problem this milestone doesn't own.
    render_result = renderer.render_translated_block(page, translated, bbox, css=css, scale_low=scale_low)

    return RedactReinsertResult(
        render_result=render_result,
        redacted_bbox=bbox,
        original_text=span.text,
        new_text=translated_text,
    )
