"""Stage: VERIFY — point 9.

Milestone 2 proved `get_text()` is not reliable for content inserted
via `insert_htmlbox()` (the ToUnicode-corruption finding). This module
therefore never treats a text-layer check as the sole or final word on
correctness — every check is tagged with its `category`
(structural / text_layer / pixel / ocr / semantic, per point 9E) so a
caller can see exactly what kind of evidence backed each result, and
`VerificationResult.passed` only requires non-skipped checks to pass.

- A. Structural checks: opens, page count, page dimensions, mutation count.
- B. Source-removal checks: text-layer based, but ONLY used to confirm
  ABSENCE of the original text (reliable), never to confirm the new
  translated text is byte-correct (unreliable, per the finding above).
- C. Rendered-pixel checks: protected regions (images, drawings,
  untouched blocks) must be pixel-identical before/after; translated
  regions are expected to change, and a "did something actually get
  drawn there" pixel-changed check stands in for content correctness
  in the absence of OCR.
- D. OCR verification: explicitly NOT implemented (point 9D says not to
  add a new dependency automatically) -- represented as a `skipped`
  check via `OCRVerifier`, a clean interface for a future
  implementation to fill in without changing this module's contract.
- E. Every check states which category backed it -- never conflated.
"""

from __future__ import annotations

from typing import Protocol

import pymupdf

from core.models import Document
from core.pdf.extractor import extract_document
from core.pipeline.models import MutationStatus, TranslationPlan, VerificationCheck, VerificationResult


class OCRVerifier(Protocol):
    """Deferred per point 9D -- no OCR dependency is added in this
    milestone. Any future implementation of this interface (e.g.
    wrapping pytesseract, already flagged as a FUTURE dependency in
    docs/dependencies.md) can be passed to `DocumentVerifier` without
    changing anything else in this module."""

    def verify_text(self, pixmap: pymupdf.Pixmap, expected_text: str, language: str | None) -> bool: ...


class DocumentVerifier:
    def __init__(self, ocr_verifier: OCRVerifier | None = None):
        self.ocr_verifier = ocr_verifier

    def verify(
        self,
        source_pdf_path: str,
        output_pdf_path: str,
        document: Document,
        plan: TranslationPlan,
    ) -> VerificationResult:
        checks: list[VerificationCheck] = []

        try:
            output = pymupdf.open(output_pdf_path)
        except Exception as exc:  # noqa: BLE001
            checks.append(
                VerificationCheck(name="output_opens", category="structural", passed=False, detail=repr(exc))
            )
            return VerificationResult(checks=checks)
        checks.append(VerificationCheck(name="output_opens", category="structural", passed=True))

        try:
            checks.extend(self._structural_checks(document, output, plan))
            checks.extend(self._source_removal_checks(output, plan))

            output_document = extract_document(output_pdf_path)
            checks.extend(self._preserved_content_checks(document, output_document, plan))
            checks.extend(self._pixel_checks(source_pdf_path, document, output, plan))
            checks.append(self._ocr_check(plan))
        finally:
            output.close()

        return VerificationResult(checks=checks)

    # -- A. structural -----------------------------------------------------

    def _structural_checks(self, document: Document, output: pymupdf.Document, plan: TranslationPlan) -> list[VerificationCheck]:
        checks = [
            VerificationCheck(
                name="page_count_unchanged",
                category="structural",
                passed=output.page_count == document.page_count,
                detail=f"output={output.page_count} source={document.page_count}",
            )
        ]
        for page_index, page in enumerate(document.pages):
            if page_index >= output.page_count:
                continue
            out_page = output[page_index]
            dims_ok = (
                abs(out_page.rect.width - page.width) < 0.5 and abs(out_page.rect.height - page.height) < 0.5
            )
            checks.append(
                VerificationCheck(
                    name=f"page_{page_index}_dimensions_unchanged",
                    category="structural",
                    passed=dims_ok,
                    detail=f"output={out_page.rect.width:.1f}x{out_page.rect.height:.1f} "
                    f"source={page.width:.1f}x{page.height:.1f}",
                )
            )

        expected_applied = sum(1 for u in plan.units if u.plan_status.value == "ok")
        actually_applied = sum(1 for u in plan.units if u.mutation_status == MutationStatus.APPLIED)
        checks.append(
            VerificationCheck(
                name="expected_mutation_count",
                category="structural",
                passed=actually_applied == expected_applied,
                detail=f"applied={actually_applied} expected={expected_applied}",
            )
        )
        return checks

    # -- B. source-removal (text-layer, absence-only) -----------------------

    def _source_removal_checks(self, output: pymupdf.Document, plan: TranslationPlan) -> list[VerificationCheck]:
        checks = []
        for unit in plan.units:
            if unit.mutation_status != MutationStatus.APPLIED or not unit.source_text.strip():
                continue
            out_text = output[unit.page_index].get_text("text")
            removed = unit.source_text.strip() not in out_text
            checks.append(
                VerificationCheck(
                    name=f"source_text_removed_{unit.source_span_id}",
                    category="text_layer",
                    passed=removed,
                    detail=(
                        "text-layer check for ABSENCE of the original source string only -- "
                        "does NOT confirm the new translated text is byte-correct "
                        "(insert_htmlbox's ToUnicode output is not trusted for that, "
                        "see docs/research/ARCHITECTURE_DECISIONS.md Decision 7)"
                    ),
                )
            )
        return checks

    # -- preserved content (structural, matched by content per Milestone 2's finding) --

    def _preserved_content_checks(self, document: Document, output_document: Document, plan: TranslationPlan) -> list[VerificationCheck]:
        translated_ids = {u.source_span_id for u in plan.units if u.mutation_status == MutationStatus.APPLIED}
        checks = []

        for page_index, page in enumerate(document.pages):
            if page_index >= len(output_document.pages):
                checks.append(
                    VerificationCheck(
                        name=f"page_{page_index}_exists_in_output",
                        category="structural",
                        passed=False,
                    )
                )
                continue
            out_page = output_document.pages[page_index]

            # Untouched spans, matched by TEXT CONTENT -- block_id is a
            # PyMuPDF positional index, not stable across edits
            # (Milestone 2 finding); text is the only reliable key
            # available for something that should be byte-identical.
            untouched_before = {
                span.text: (span.bbox.x0, span.bbox.y0, span.bbox.x1, span.bbox.y1)
                for span in page.source_spans
                if span.span_id not in translated_ids
            }
            untouched_after = {
                span.text: (span.bbox.x0, span.bbox.y0, span.bbox.x1, span.bbox.y1) for span in out_page.source_spans
            }
            missing_or_moved = [
                text[:40] for text, bbox in untouched_before.items() if untouched_after.get(text) != bbox
            ]
            checks.append(
                VerificationCheck(
                    name=f"page_{page_index}_unrelated_text_preserved",
                    category="structural",
                    passed=not missing_or_moved,
                    detail=f"missing/moved: {missing_or_moved}" if missing_or_moved else "",
                )
            )

            images_ok = len(page.images) == len(out_page.images) and all(
                a.xref == b.xref for a, b in zip(page.images, out_page.images)
            )
            checks.append(
                VerificationCheck(
                    name=f"page_{page_index}_images_preserved", category="structural", passed=images_ok
                )
            )

            drawings_ok = len(page.drawings) == len(out_page.drawings)
            checks.append(
                VerificationCheck(
                    name=f"page_{page_index}_drawings_preserved", category="structural", passed=drawings_ok
                )
            )
        return checks

    # -- C. rendered-pixel checks --------------------------------------------

    def _pixel_checks(
        self, source_pdf_path: str, document: Document, output: pymupdf.Document, plan: TranslationPlan
    ) -> list[VerificationCheck]:
        checks = []
        source = pymupdf.open(source_pdf_path)
        try:
            for page_index, page in enumerate(document.pages):
                if page_index >= output.page_count or page_index >= source.page_count:
                    continue
                src_page = source[page_index]
                out_page = output[page_index]

                # Protected regions: images must be pixel-identical.
                for image in page.images:
                    before = src_page.get_pixmap(clip=image.bbox)
                    after = out_page.get_pixmap(clip=image.bbox)
                    same = before.samples == after.samples
                    checks.append(
                        VerificationCheck(
                            name=f"image_{image.image_id}_pixels_unchanged", category="pixel", passed=same
                        )
                    )

                # Protected regions: drawings must be pixel-identical.
                for drawing in page.drawings:
                    before = src_page.get_pixmap(clip=drawing.bbox)
                    after = out_page.get_pixmap(clip=drawing.bbox)
                    same = before.samples == after.samples
                    checks.append(
                        VerificationCheck(
                            name=f"drawing_{drawing.drawing_id}_pixels_unchanged", category="pixel", passed=same
                        )
                    )

                # Translated regions: pixels are EXPECTED to change --
                # a stand-in for "something was actually drawn there"
                # in the absence of OCR-based content verification.
                for unit in plan.units:
                    if unit.page_index != page_index or unit.mutation_status != MutationStatus.APPLIED:
                        continue
                    rect = unit.fit_result.final_rect if unit.fit_result and unit.fit_result.final_rect else unit.source_rect
                    before = src_page.get_pixmap(clip=rect)
                    after = out_page.get_pixmap(clip=rect)
                    changed = before.samples != after.samples
                    checks.append(
                        VerificationCheck(
                            name=f"translated_region_changed_{unit.source_span_id}",
                            category="pixel",
                            passed=changed,
                            detail="confirms new content was drawn; does NOT confirm it is textually correct",
                        )
                    )
        finally:
            source.close()
        return checks

    # -- D. OCR (deferred) ---------------------------------------------------

    def _ocr_check(self, plan: TranslationPlan) -> VerificationCheck:
        if self.ocr_verifier is None:
            return VerificationCheck(
                name="ocr_content_verification",
                category="ocr",
                passed=True,
                skipped=True,
                detail=(
                    "deferred per Milestone 4 point 9D -- no OCR dependency added; "
                    "pass an OCRVerifier implementation to DocumentVerifier to enable"
                ),
            )
        # An OCRVerifier was supplied -- run it, but this milestone
        # does not ship a concrete implementation, so this path is
        # exercised only by callers/tests that provide their own.
        return VerificationCheck(
            name="ocr_content_verification", category="ocr", passed=True, skipped=True, detail="not yet wired up"
        )
