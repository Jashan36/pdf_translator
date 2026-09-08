---
name: visual-pdf-qa
description: Compare an original PDF page against its translated/reconstructed version to catch clipping, overflow, missing text/images, geometry drift, and font problems. Use after any code path that produces or modifies an output PDF, before considering that output acceptable.
---

# Visual PDF QA

A translated PDF is not done until it passes this. Never treat "the
code ran without an exception" as success for a rendering change.

## Procedure (master plan Section 36-37)

```text
original.pdf  → render page to PNG
translated.pdf → render page to PNG
              → compare
```

1. **Render both pages at the same DPI/scale** (PyMuPDF
   `page.get_pixmap()`), so pixel comparison is meaningful.
2. **Don't treat every pixel difference as an error.** Translated text
   is *expected* to differ from source text. Split the page into
   region masks before judging:
   - **Protected regions** (logos, photographs, background, decorative
     shapes, anything not translated) — differences here should be
     near zero. Any visible diff means something leaked geometry/color
     changes it shouldn't have.
   - **Text regions** (translated content) — differences are expected;
     evaluate position, clipping, overflow, style, color, baseline, and
     font-size deviation instead of raw pixel diff.
3. **Check structural invariants directly, not just visually**:
   - page count unchanged
   - page dimensions unchanged (deviation = 0)
   - image geometry unchanged (deviation = 0) unless image-text
     localization was explicitly requested
   - no text clipped outside its bounding box
   - no translated text overlapping a protected object
4. **Surface concrete warnings, not a vague pass/fail**:
   - `⚠ Text overflow`
   - `⚠ Font reduced from 18pt to 15pt`
   - `⚠ Missing target glyph`
   - `⚠ Possible numerical mismatch` (defer to `translation-quality`
     for the actual check, but flag it here if detected)
5. **Produce per-page confidence scores** (layout_score,
   translation_score if available, semantic_score) rather than a
   single opaque "looks fine" — these are engineering diagnostics, not
   a claim of human-level correctness (Section 40).
6. **Never silently accept a damaged page.** If a block couldn't fit
   even after the text-fit engine's fallbacks, that's a `LAYOUT_WARNING`
   for human review (Section 56), not something QA should paper over.

## When this applies

Any time a PDF has just been generated or modified by this project's
own code (Milestone 2 onward) — run this before telling the user the
output is ready, and before any commit that claims a rendering feature
"works".
