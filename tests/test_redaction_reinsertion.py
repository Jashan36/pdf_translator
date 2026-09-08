"""Milestone 2 point 9: single-block redact/reinsert proof.

Deliberately narrow, per instructions: prove ONE source text block can
be identified, isolated, safely redacted, reinserted via
`insert_htmlbox`, rendered correctly, and compared against the
original geometry — on one controlled test page. This is NOT a
whole-document replacement pipeline (that's a later milestone).

Text-layer verification of the NEW content deliberately does not use
`page.get_text()` — see `docs/research/ARCHITECTURE_DECISIONS.md`
Decision 7's Milestone-2 update: `insert_htmlbox` output was found to
corrupt the PDF's ToUnicode text layer even though it renders visually
correctly. Verification here instead checks (a) the ORIGINAL text is
gone from the page's text layer -- which does not depend on the new
content's CMap correctness -- and (b) the new content actually
rendered (non-blank pixels, no clipping), matching the visual-QA
philosophy in the `visual-pdf-qa` skill.
"""

from pathlib import Path

import pymupdf
import pytest

from core.pdf.extractor import extract_document
from core.pdf.redact_reinsert import redact_and_reinsert_span

GOLDEN = Path(__file__).parent / "fixtures" / "golden_multilingual.pdf"
FONTS_DIR = Path(__file__).resolve().parents[1] / "fonts"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "research" / "assets" / "redact-reinsert-proof"


@pytest.fixture()
def golden_document():
    return extract_document(str(GOLDEN))


def _telugu_span(document):
    page = document.pages[0]
    block = next(b for b in page.blocks if "పరీక్ష" in b.raw_text)
    return block.lines[0].spans, block


def test_single_block_redact_and_reinsert_telugu(golden_document, tmp_path):
    spans, original_block = _telugu_span(golden_document)
    # The block is one line of Telugu text extracted as (possibly
    # several) spans -- treat the whole line as the target region,
    # matching how a real translation unit (a "block", per master plan
    # Section 8) would be handled, not an individual PDF span.
    target_span = spans[0]
    original_text = original_block.raw_text

    # Record the rest of the page's geometry BEFORE any modification,
    # to verify against afterward (step 6: "compare against the
    # original geometry"). Keyed by TEXT, not block_id: block_id is
    # derived from PyMuPDF's positional "number" field (see
    # core/pdf/extractor.py), which is a snapshot-local index, not a
    # stable identifier across edits -- redacting one block shifts
    # every later block's "number" in a fresh extraction. Content is
    # the only stable key available for an untouched block across a
    # before/after re-extraction; this is itself a real Milestone 2
    # finding, recorded in PROJECT_STATE.md's known limitations.
    other_blocks_before = {
        b.raw_text: (b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1)
        for b in golden_document.pages[0].blocks
        if b.block_id != original_block.block_id
    }
    image_before = golden_document.pages[0].images[0]

    # Open a live, mutable copy of the PDF (extraction closed its own).
    pdf = pymupdf.open(str(GOLDEN))
    page = pdf[0]

    new_telugu_text = "కొత్త అనువాదం ఇక్కడ ఉంది."  # "A new translation is here." -- different from the original
    font_dir = FONTS_DIR / "telugu"
    result = redact_and_reinsert_span(
        page,
        target_span,
        new_telugu_text,
        font_family="NotoSansTelugu",
        font_filename="NotoSans-telugu.ttf",
        font_archive=pymupdf.Archive(str(font_dir)),
    )

    # Step 5 (rendered correctly): insert_htmlbox reported a successful fit.
    assert result.render_result.ok, f"reinsertion failed to fit: {result.render_result}"
    # A little shrinkage vs. the source span's tight extraction bbox is
    # expected (see redact_and_reinsert_span's scale_low docstring) --
    # this is not the text-fit engine (Milestone 3), so just sanity
    # check the scale wasn't reduced to something illegibly small.
    assert result.render_result.scale > 0.3

    out_pdf = tmp_path / "redact_reinsert_proof.pdf"
    pdf.save(str(out_pdf))
    pdf.close()

    # Also keep a copy + rendered PNG as visual evidence, alongside the
    # other Milestone 2 research artifacts.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(str(out_pdf)) as verify_doc:
        verify_page = verify_doc[0]

        # Step 6a: the ORIGINAL text must be gone from the page's text
        # layer. This does not depend on insert_htmlbox's CMap
        # correctness -- it's checking absence, not the new content.
        remaining_text = verify_page.get_text("text")
        assert original_text not in remaining_text

        # Step 6b: every OTHER block's geometry is unaffected -- the
        # redaction was scoped tightly enough not to collaterally
        # damage anything else on the page. Matched by text content,
        # not block_id (see the "before" comment above for why).
        verify_document = extract_document(str(out_pdf))
        other_blocks_after = {b.raw_text: (b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1) for b in verify_document.pages[0].blocks}
        for text, before_bbox in other_blocks_before.items():
            assert other_blocks_after.get(text) == before_bbox, (
                f"block {text!r} geometry changed: {before_bbox} -> {other_blocks_after.get(text)}"
            )

        # Image untouched (redaction was scoped to text only).
        image_after = verify_document.pages[0].images[0]
        assert image_after.xref == image_before.xref
        assert (image_after.bbox.x0, image_after.bbox.y0) == (image_before.bbox.x0, image_before.bbox.y0)

        # Step 5/visual proof: render the target rect and confirm it is
        # not blank (something was actually drawn, not just "no error").
        pix = verify_page.get_pixmap(clip=result.redacted_bbox, matrix=pymupdf.Matrix(3, 3))
        assert pix.samples != b"\xff" * len(pix.samples), "target rect is blank after reinsertion"

        # Save proof artifacts for manual/visual review.
        verify_doc.save(str(OUT_DIR / "proof.pdf"))
        full_pix = verify_page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        full_pix.save(str(OUT_DIR / "proof_full_page.png"))
        pix.save(str(OUT_DIR / "proof_target_rect.png"))
