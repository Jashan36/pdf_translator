# Visual QA — Research Findings

Scope: Section K. Detecting missing text, clipping, overflow, moved
text, changed page geometry, missing images, font failures,
unexpected blank areas, page-count changes — refining master plan
Sections 36–37.

Date checked: 2026-09-08.

---

## 1. Raw pixel diff

Simplest method: render both PDFs to same-DPI PNGs (verified API:
`page.get_pixmap(dpi=...)`, `pix.save(...)` —
pymupdf.readthedocs.io/en/latest/recipes-images.html, official docs)
and compute an absolute difference image (`D = |I_original -
I_translated|`, as master plan Section 37 already specifies).

Strength: catches any visual change at all, including subtle
rendering artifacts. Weakness: since translated text is **expected**
to differ from original text (different script entirely for Indic
languages), raw pixel diff over the whole page is nearly useless
without region masking — master plan Section 37 already recognizes
this ("do NOT interpret every difference as an error... create region
masks"). Raw pixel diff is therefore only meaningful when restricted
to **protected regions** (logos, photos, backgrounds, decorative
shapes) where near-zero diff is the expected/correct outcome.

## 2. SSIM (Structural Similarity Index)

Verified against scikit-image's own API docs
(scikit-image.org/docs/stable/api/skimage.metrics.html, official
project docs):

```python
skimage.metrics.structural_similarity(
    im1, im2, win_size=None, gradient=False, data_range=None,
    channel_axis=None, gaussian_weights=False, full=False, **kwargs
)
```

SSIM measures perceptual similarity based on **luminance, contrast,
and structure**, not raw pixel-value difference — this makes it more
robust to minor anti-aliasing/rendering noise than raw pixel diff,
while still being localizable: passing `full=True` returns a full
per-pixel SSIM map (`S`), which can be used the same way as a
difference heatmap (master plan Section 36 item 3) but with a more
perceptually meaningful score than raw pixel delta. Good fit for
**protected regions** where near-zero pixel change is expected but
some rendering-engine anti-aliasing noise should not trigger a false
positive.

## 3. Perceptual image hashing

General technique (not tool-specific to this project, common
libraries: `imagehash`/pHash). Reduces an image to a compact hash
robust to small transformations (compression, minor resizing);
comparison is a Hamming distance between hashes. Useful as a fast
coarse pre-filter (e.g. "did this page change at all, at a whole-page
level?") but too coarse for the fine-grained checks this project
needs (clipping, single-line text shifts) — recommend using it only
as an optional cheap first-pass gate before spending SSIM/pixel-diff
budget, not as a primary signal.

## 4. Bounding-box comparison (geometry, not pixels)

Verified via PyMuPDF's own documented extraction API:
`page.get_text("dict")` returns block/line/span bounding boxes in
points along with font name/size/color per span
(pymupdf.readthedocs.io/en/latest/app1.html, official docs — same API
already relied on in the layout-fitting research above). This lets QA
compare **structure**, not pixels:

- Did a text block's bbox move beyond a tolerance vs. the geometry the
  layout-fit engine intended? (Detects "moved text" directly and
  deterministically — no rendering/pixel noise involved.)
- Did a span's bbox extend beyond its parent block/page bbox?
  (Detects clipping/overflow deterministically.)
- Did the count/set of image XObjects on the page change?
  (Detects missing images.)
- Did the reported font name for a span silently fall back to a
  different font than intended? (Detects font failures — e.g. an
  Indic glyph silently rendered in a fallback font because the
  primary font lacked the glyph.)

This is the **most precise and cheapest** check available for exactly
the failure modes the task lists (missing text, clipping, overflow,
moved text, missing images, font failures) because it operates on the
PDF's own structured data rather than inferring these facts from
pixels. It should be the QA system's primary/first-line check, not an
afterthought.

## 5. OCR-based comparison

Verified via `pytesseract`'s official GitHub repository
(github.com/madmaze/pytesseract): `image_to_string(image, lang=...,
config=..., timeout=...)` is confirmed as a thin Python wrapper around
the Tesseract OCR engine (which must be installed separately), with
`lang` accepting multi-language strings like `'eng+hin'`. Use case: OCR the rendered
translated PDF page image and compare recognized text against the
expected translated text (or against extracted PDF text run through
the same rendering path) to catch:

- Missing text that PDF-structure extraction alone would not catch if
  the failure is at the rendering/rasterization layer (e.g. a glyph
  that exists in the PDF's text objects but renders as a blank/box
  glyph due to a font substitution problem — this can look
  "structurally present" via `get_text("dict")` but be visually
  absent).
- A sanity check that pixel-level rendering actually matches intended
  text content, independent of the geometry check in Section 4.

Caveat (own reasoning, not sourced from an official doc): OCR accuracy
on Indic scripts is itself imperfect and depends on the Tesseract
language pack quality for each script; OCR mismatches should be
treated as **flags for review**, not hard failures, to avoid false
positives from OCR error rather than actual rendering defects.

## 6. Structural/geometric comparison (page-level)

Cheapest, most deterministic checks, all available directly from
PyMuPDF's document object model (`len(doc)` for page count,
`page.rect` for page dimensions — both basic, already-relied-on
PyMuPDF APIs per the official docs' "The Basics" page):

- Page count unchanged (unless intentionally expected, e.g. content
  overflow to a new page — should be flagged either way).
- Page dimensions (`page.rect.width/height`) unchanged.
- Object counts (images, annotations, form fields) unchanged unless
  an intentional change occurred.

These checks are near-zero-cost and should run first, before any
pixel or OCR work, as a fast fail-fast gate.

---

## Recommended hybrid QA approach

No single method above covers every failure mode the task lists —
this is the central conclusion, and it matches master plan Section
36's own instruction to generate multiple outputs (side-by-side,
overlay, heatmap, warnings) rather than a single score. Concretely:

| Failure mode | Primary check | Secondary/confirming check |
|---|---|---|
| Page count change | Structural (`len(doc)`) | — |
| Changed page geometry | Structural (`page.rect`) | Pixel diff on whole page as sanity check |
| Missing text | Bounding-box/geometry diff of extracted spans (text present in structure) | OCR comparison (text actually rendered/visible) |
| Clipping / overflow | Bounding-box comparison (span bbox vs. parent/page bbox) | Pixel diff in the specific region flagged |
| Moved text | Bounding-box comparison vs. intended layout-fit geometry | — |
| Missing images | Structural (image XObject count/id diff) | Pixel diff in that region |
| Font failures (wrong glyph/fallback/box glyphs) | Structural (span font-name diff) | OCR comparison (visually garbled/missing = OCR will also fail to recognize it) |
| Unexpected blank areas | Pixel diff / SSIM against expected non-blank region | Bounding-box check (is a spanned area empty of any span/image where one was expected?) |
| Protected-region fidelity (logos, photos, backgrounds) | SSIM (perceptually robust near-zero-diff check) | Raw pixel diff as a stricter secondary confirmation |

Rationale for the split:

- **Structural/geometric checks are cheapest and most deterministic**
  — run them first as a fail-fast layer (page count, dimensions, span
  bboxes, font names, object counts) sourced directly from PyMuPDF's
  own document model, not from re-deriving facts out of pixels.
- **Pixel-based checks (raw diff, SSIM) are reserved for regions where
  a human/visual definition of "correct" genuinely requires looking
  at pixels** — protected regions (near-zero expected diff) and
  catching rendering-engine-level defects (garbled glyphs, wrong
  anti-aliasing, unexpected blank space) that pure structural
  extraction cannot see because the PDF's internal text objects can
  look fine while still rendering wrong.
- **OCR-based checks are the correctness bridge between "text objects
  exist in the PDF" (structural) and "the reader can actually read
  it" (pixel)** — they catch the specific and important failure mode
  of Indic-script rendering going wrong at the glyph level even though
  the PDF's text spans are structurally present (directly relevant
  given the topic-I finding that naive text insertion can produce
  garbled/incorrect glyph sequences for Indic scripts).
- Relying on any single method is insufficient: pixel diff alone
  cannot distinguish "expected translation-driven text change" from
  "layout defect"; structural bbox comparison alone cannot see
  glyph-level rendering failures (a span can have a perfectly correct
  bbox and font name while still rendering a garbled glyph sequence
  due to an Indic shaping bug); OCR alone is unreliable for exact
  geometry (clipping/overflow) and has its own error rate.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| scikit-image | `skimage.metrics.structural_similarity` API reference | https://scikit-image.org/docs/stable/api/skimage.metrics.html | Official docs | 2026-09-08 | current stable | SSIM measures luminance/contrast/structure similarity; `full=True` returns a per-pixel SSIM map usable as a heatmap |
| PyMuPDF | Images recipes (get_pixmap/save) | https://pymupdf.readthedocs.io/en/latest/recipes-images.html | Official docs | 2026-09-08 | current | `page.get_pixmap(dpi=...)` + `pix.save()` render page to PNG for pixel-based comparison |
| PyMuPDF | Appendix 1: Details on Text Extraction | https://pymupdf.readthedocs.io/en/latest/app1.html | Official docs | 2026-09-08 | current | `get_text("dict")` gives block/line/span bboxes and font info for structural/geometric QA |
| pytesseract | pytesseract OCR wrapper (official repo) | https://github.com/madmaze/pytesseract | Official GitHub repo | 2026-09-08 | Apache 2.0, Python 3.6+ | `image_to_string(image, lang=..., config=..., timeout=...)` confirmed; `lang` supports multi-language e.g. `'eng+fra'`; requires Tesseract engine installed separately |
