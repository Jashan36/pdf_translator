---
name: pdf-forensics
description: Inspect a PDF's actual internal structure with PyMuPDF before modifying, translating, or reasoning about it — determine native vs OCR vs vector vs raster text, and extract blocks/lines/spans/bboxes/fonts/images/colors/rotation/reading order. Use before any PDF-editing or layout-reasoning task in this project.
---

# PDF Forensics

Never assume a PDF's structure from how it looks when rendered. A PDF
that "looks like text" may actually be:

- **native text** — real text objects with span metadata (highest
  fidelity path, use PyMuPDF directly)
- **OCR'd / scanned** — page images with no extractable text
- **vector outlines** — glyphs drawn as paths, not text objects
- **mixed** — different pages or regions use different strategies

## Procedure

1. **Classify before extracting.** Sample several pages
   (`page.get_text("text")`); if extractable text is near-empty, treat
   the PDF as Class B (scanned) — extraction will need OCR (a later
   milestone), not more PyMuPDF tuning. See `core/pdf/analyzer.py:
   is_native_text_pdf`.
2. **Extract at span level, not page level.** Use
   `page.get_text("dict")` to get blocks → lines → spans. Each span
   carries `text`, `bbox`, `font`, `size`, `flags`, `color` — pull all
   of them, don't re-derive geometry by eyeballing a render.
3. **Distrust font flags in isolation.** PDF font programs can have
   incorrect/incomplete `flags`. Cross-check bold/italic against the
   font name string (e.g. `"bold"` / `"italic"` substrings) as a
   fallback heuristic — see `_font_from_span` in
   `core/pdf/analyzer.py`.
4. **Record images and vectors as objects with their own bbox**, via
   `page.get_images(full=True)` + `page.get_image_rects(xref)` for
   images. Never assume an image's rendered position — always resolve
   its rect.
5. **Preserve rotation.** Compute line direction from the `dir` vector
   (`atan2(dir_y, dir_x)`), don't assume upright text.
6. **Write results into the internal Document model** (`core/models.py`),
   never into ad-hoc dicts — downstream layers (translation, layout,
   QA) depend on that shape.
7. **Store the original geometry before any modification.** Milestone
   2+ code that replaces or re-renders text must diff against this
   forensics output, not against a fresh re-read of an already-edited
   PDF.

## When this applies

Any time you're about to: read a PDF's contents, decide how to
translate it, replace text in it, or evaluate whether an output PDF
matches an input PDF. If you find yourself writing code that assumes
"the text is probably at roughly this position" — stop, and extract
the real bbox instead.

## Reference

`core/pdf/analyzer.py` is the canonical implementation. Extend it
rather than writing a parallel extraction path elsewhere.
