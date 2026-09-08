# PyMuPDF — Technical Research (current release)

Date checked: 2026-09-08
Current stable release verified: **PyMuPDF 1.28.2** (released 2026-08-06), built on MuPDF 1.28.0.
License: Dual licensed — GNU AGPL 3.0 or Artifex commercial license.
Python compatibility: Python >= 3.10 (wheels for 3.10–3.14).

Sources: https://pypi.org/project/PyMuPDF/ , https://github.com/pymupdf/PyMuPDF/releases

> Note on method: WebFetch/WebSearch tools were used against the live
> `pymupdf.readthedocs.io` "latest" docs and the GitHub repo. Some
> WebFetch calls returned partial/paraphrased content because the small
> summarizer model condenses the fetched page — where a fact could not
> be directly quoted from the fetched excerpt, that is noted below.
> Nothing here is drawn from training-data memory of older PyMuPDF
> versions; every claim is tied to a fetch against the current docs.

---

## 1. `page.get_text()` output modes

Source: https://pymupdf.readthedocs.io/en/latest/textpage.html (fetched 2026-09-08)

`get_text()` is a convenience wrapper around `TextPage` extraction. Confirmed modes:

- **`"text"`** — plain UTF-8 string of the page's text; can be sorted top-to-bottom/left-to-right for a "natural" reading order (`sort=True`), but this is a positional heuristic, not a semantic reading order (see Part B).
- **`"blocks"`** — list of tuples `(x0, y0, x1, y1, "text", block_no, block_type)` where `block_type` is `0` = text, `1` = image, and (per the blocks description) vector-drawing blocks can also appear, "in the same order as they are present in the page's contents stream" — i.e. draw order, not visual/logical order.
- **`"words"`** — list of tuples `(x0, y0, x1, y1, "word", block_no, line_no, word_no)`; custom word-delimiters supported since v1.23.5.
- **`"dict"` / `"rawdict"`** — nested Python dict: `{"width", "height", "blocks":[...]}`. `dict` gives span-level text; `rawdict` additionally breaks each span into individual `"chars"`.
- **`"json"` / `"rawjson"`** — same hierarchy as dict/rawdict, JSON-serializable (images base64-encoded instead of binary).
- **`"html"` / `"xhtml"` / `"xml"`** — formatted reconstructions with positioning info; HTML embeds images as base64.

## 2. Block/line/span/char structure (dict / rawdict)

Source: https://pymupdf.readthedocs.io/en/latest/app1.html (fetched 2026-09-08)

```
page dict
 ├── width, height
 └── blocks[]
      ├── type            (0 = text, other = image)
      ├── bbox            (x0, y0, x1, y1)
      └── lines[]                      # text blocks only
           ├── wmode      (0 = horizontal)
           ├── dir        (e.g. (1.0, 0.0) — writing direction vector)
           ├── bbox
           └── spans[]
                ├── size, flags, font, color
                ├── origin   (x, y) — glyph origin, not top-left
                ├── bbox
                ├── text     ("dict" mode)
                └── chars[]  ("rawdict" mode only)
                     ├── c        (single character)
                     ├── origin
                     └── bbox     (per-character bbox)
```

So **bounding boxes exist at block, line, span, and (in rawdict) individual-character level** — this is the finest granularity PyMuPDF exposes natively.

## 3. Font metadata per span, and flag reliability

Source: https://pymupdf.readthedocs.io/en/latest/textpage.html

Each span carries `font` (name string), `size` (float), `flags` (int bitfield encoding italic/serif/bold/monospace-type properties), and `color` (int, typically sRGB packed). The docs explicitly warn:

> "this information is not necessarily correct or complete: fonts quite often contain wrong data here"

This directly confirms the master plan's Section 21 caution — **font `flags` cannot be trusted alone** to decide bold/italic; the project's plan to combine "PDF metadata + visual inspection + fallback heuristics" is consistent with the documented caveat, not overkill.

## 4. Image extraction

Sources: https://pymupdf.readthedocs.io/en/latest/page.html , https://pymupdf.readthedocs.io/en/latest/document.html (fetched 2026-09-08)

- `Page.get_images(full=False)` — "PDF only: get list of referenced images" on the page (i.e., images the page's resources *reference*, not necessarily images actually painted/visible).
- `Page.get_image_rects()` — "improved version of `Page.get_image_bbox()`"; gives the actual placement rectangle(s) of a given image xref on the page.
- `Document.extract_image(xref)` — "PDF only: extract an embedded image by xref", returning the raw image bytes/extension/colorspace data for that object.
- **Documented limitation** (from `document.html`): image xrefs obtained by parsing PDF objects are, in general, **"not the list of images that are actually displayed"** — for accurate on-page image usage, the docs point to `Page.get_image_info()` instead of naively trusting `get_images()`.

## 5. Vector drawings

Source: https://pymupdf.readthedocs.io/en/latest/page.html

`Page.get_drawings()` returns the page's vector graphics as a list of dicts (fetch surfaced keys including `items`, `fill`, `color`, `width`, `closePath`, `rect`/bbox-like fields, and `type` per path). This is the mechanism for detecting/preserving lines, shapes, borders, and other non-text, non-raster graphics so they are not accidentally destroyed during text replacement.

## 6. Annotations

Source: https://pymupdf.readthedocs.io/en/latest/page.html

`Page.annots(types=None)` iterates `Annot` objects on the page; `Page.first_annot` gives the first one. Annotations (comments, links-as-annotations, redaction marks, form widgets, etc.) are a distinct PDF object layer from page content-stream text/graphics — they must be enumerated and handled separately from `get_text()`/`get_drawings()` extraction.

## 7. Redaction (`apply_redactions`) — how it actually works

Sources: https://pymupdf.readthedocs.io/en/latest/page.html , corroborated by https://github.com/pymupdf/PyMuPDF/discussions/3422 and the PyMuPDF FAQ (fetched 2026-09-08)

Two-step, by design:

1. `Page.add_redact_annot(quad, text=None, fontname=None, fontsize=11, align=TEXT_ALIGN_LEFT, fill=(1,1,1), text_color=(0,0,0), cross_out=True)` — stages a redaction annotation over a quad/rect. Optionally carries replacement `text` to be stamped in on apply, with limited formatting (font/size/align only — the docs note automatic font-size shrink-to-fit down to a floor, reported elsewhere as 4pt).
2. `Page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS, graphics=PDF_REDACT_LINE_ART_REMOVE_IF_COVERED, text=PDF_REDACT_TEXT_REMOVE)` — **"Remove all content contained in any redaction rectangle on the page. This method applies and then deletes all redactions from the page."** This is a real, permanent content removal (unlike a visual black-box overlay) — the underlying text/graphics operators inside the rectangle are actually deleted from the content stream, not just hidden.
   - `images=`: controls how images overlapping the rect are handled (default blanks the covered pixels; other flags can fully remove or ignore the image).
   - `graphics=`: controls vector art overlapping the rect (ignore / remove-if-covered / remove-if-touched).
   - `text=`: default removes any character whose bbox overlaps the rectangle; can be told to preserve text instead (rarely useful for a redaction, but relevant if you're reusing this API purely to blank a region without also destroying nearby glyphs).

FAQ-corroborated pattern for full control (rather than relying on `add_redact_annot`'s built-in limited-formatting replacement text): apply the redaction to clear the area, **then** call `insert_text()` / `insert_htmlbox()` separately in a second pass with full control over font, styling, and wrapping.

## 8. `insert_text` / `insert_textbox` / `insert_htmlbox`

Source: https://pymupdf.readthedocs.io/en/latest/page.html (fetched 2026-09-08)

- `Page.insert_text(point, text, fontsize=11, fontname='helv', fontfile=None, idx=0, color=None, fill=None, render_mode=0, rotate=0, ...)` — inserts text as new content-stream operators anchored at a **baseline point**, using either a builtin/base-14 font or a font file you supply. It does **not** perform layout: no automatic wrapping, no line breaking, no reflow — you must pre-compute line breaks and re-call it per line. It does not preserve any pre-existing formatting of the "replaced" text; it only draws exactly what you give it.
- `Page.insert_textbox(rect, buffer, align=TEXT_ALIGN_LEFT, border_width=1, color=None, fontsize=11, ...)` — inserts text into a rectangle with basic word-wrap and alignment. If the text does not fit, the caller must choose: accept a no-op/overflow report, or let it auto-shrink (`scale_low` default 0 meaning "scale down until it fits"). It returns a fit-status value the caller inspects (documented in the FAQ pattern: "reduce font size until [return value from insert_textbox] is positive"). It does not preserve character-level style variation (mixed bold/italic within one string, per-character color, kerning identical to the source) — it's a single uniform run of one font/size/color per call.
- `Page.insert_htmlbox(rect, text, *, css=None, scale_low=0, archive=None, rotate=0, oc=0, opacity=1, overlay=True)` — a newer, more capable API that accepts (a subset of) HTML + CSS, giving finer per-run styling and (per the FAQ) more graceful overflow handling than `insert_textbox`. This is the closest built-in tool to "reinsert richly-styled translated text" without hand-rolling layout.

**None of the insertion APIs automatically infer or reuse the original span's exact style** (font program, exact color, exact tracking) — the caller must carry that forward explicitly from the extracted span metadata (font name/size/color/flags) captured in step 1, matching the master-plan document model (Section 5/21).

## 9. Text measurement

Sources: https://pymupdf.readthedocs.io/en/latest/functions.html , https://pymupdf.readthedocs.io/en/latest/font.html (fetched 2026-09-08)

- Module-level `pymupdf.get_text_length(text, fontname='helv', fontsize=11, encoding=TEXT_ENCODING_LATIN)` — returns the rendered width in points for a **builtin Base-14 font or CJK font only**; does not work for arbitrary embedded/external fonts.
- `Font(fontname_or_file).text_length(text, fontsize=11)` — the general-purpose version that works with any loaded `Font` object (builtin, CJK, or a custom font file you load), so this is the one to use for target-language fonts such as Noto Sans Telugu/Devanagari (Section 22 of the master plan). If a character is missing from the font it is "automatically looked up in a fallback font" — worth knowing since that fallback substitution could silently change the rendered glyph's width/appearance.
- This directly answers the master plan's Section 19 text-fit algorithm need: **before** committing to a font size, measure the translated string with `Font(target_font).text_length(text, size)` against the available width, exactly as Section 19 describes ("measure translated text… if required_width <= available_width").

## 10. Page rendering for QA

Source: https://pymupdf.readthedocs.io/en/latest/page.html

`Page.get_pixmap(matrix=..., dpi=..., colorspace=..., alpha=..., clip=...)` rasterizes the page (or a clipped region) to a `Pixmap`, usable for visual diffing between original and translated pages (master plan Section 36–37 Visual QA). Parameters exist to scale (via `matrix`/`dpi`), pick a colorspace, control alpha, and restrict to a sub-rectangle (`clip`) — useful for rendering just a protected region for comparison.

## 11. Low-level PDF object (xref) inspection

Source: https://pymupdf.readthedocs.io/en/latest/document.html (fetched 2026-09-08)

PyMuPDF exposes raw COS-object access, not just the interpreted page/text/image API layer:

- `Document.xref_object(xref)` — raw PDF object source for that xref.
- `Document.xref_get_keys(xref)` — dictionary keys present on that object.
- `Document.xref_get_key(xref, key)` / `xref_set_key(xref, key, value)` — read/write a specific PDF dictionary key's (type, value).
- `Document.xref_stream_raw(xref)` — raw (undecoded) stream bytes for a stream object.

This is the escape hatch for anything the high-level API doesn't model (e.g. inspecting a font dictionary's `/FontFile2`, an Optional Content Group's visibility state, or a `/StructTreeRoot` if present) — relevant to Part B's structural facts below.

---

## Answers to the explicit questions

### 1. What CAN be reliably recovered from a native-text PDF via PyMuPDF?

- Exact visual/geometric facts: page size/rotation, block/line/span/char bounding boxes, glyph origins, span-level font name/size/color, image placement rectangles and raw image bytes, vector-drawing paths/fills/strokes, and a rasterized rendering of any page/region for QA. All of this is directly exposed by `get_text("dict"/"rawdict")`, `get_images`/`get_image_rects`/`extract_image`, `get_drawings`, and `get_pixmap` (sources above). This matches what the master plan calls "geometry" — it's what PyMuPDF is authoritative on.
- Actual characters that make up the text (when the PDF has real, non-scanned text with valid encoding — see ToUnicode discussion in Part B), because `get_text()` decodes character codes via the font's encoding/CMap.
- Low-level PDF object internals (xref dictionaries, raw streams) for anything not modeled by the high-level API.

### 2. What CANNOT be reliably recovered?

- **Semantic structure.** "Paragraph," "section," "heading," "table," "reading order" are **not native PyMuPDF (or even native PDF, see Part B) concepts** for an untagged PDF — PyMuPDF gives you positioned blocks/lines/spans in content-stream order (or position-sorted order with `sort=True`), and the project must *infer* paragraphs/sections/reading order from that geometry (this is exactly why the master plan's Section 5 "Document Understanding Layer" and Section 17 "third pass: build semantic groups" exist as a separate inference step, not something to expect `get_text()` to hand over).
- **Guaranteed-correct font style flags** (bold/italic/etc.) — explicitly documented as sometimes wrong in the source PDF's font data (Section 3 above).
- **A definitive list of images actually painted on the page** from `get_images()` alone — documented as potentially including referenced-but-unused images; `get_image_info()` is the more accurate cross-check (Section 4 above).
- **Structural provenance of a "font" name across a document** — a font `name` string is a per-page/per-object label, not necessarily a stable global identity if the same visual font is embedded as multiple subsetted font objects (a known PDF-generation pattern the plan should watch for even though it wasn't separately verified as a numbered doc claim here).

### 3. Safest documented method to replace text while preserving everything else

There is **no single built-in "replace this span's text" call**. The current officially-documented and community-corroborated pattern (FAQ + `page.html` + GitHub discussion #3422, all fetched 2026-09-08) is:

1. Extract spans with `get_text("dict")`/`"rawdict"` to capture exact bbox + font + size + color per span (this is your record of "what was there").
2. Stage a redaction over that span's rectangle with `add_redact_annot()` (optionally supplying simple built-in replacement text if the limited auto-formatting is acceptable).
3. Call `apply_redactions()` to actually delete the underlying text (and, per your `images=`/`graphics=` flags, control what happens to any image/vector-art overlapping that rectangle — default behavior blanks covered image pixels and conditionally strips covered vector art, so **redacting a text rectangle can destroy nearby non-text content if the rectangle is drawn too generously**).
4. Reinsert the translated text in a second pass with `insert_text()`, `insert_textbox()`, or `insert_htmlbox()`, driving font/size/color explicitly from the span metadata captured in step 1 (and from the text-fit algorithm in Section 19 of the plan, using `Font.text_length()` from Section 9 above to decide whether it fits at the original size).

**Tradeoffs:**
- This is destructive-then-reconstructive, not a true "edit in place" — you are responsible for carrying forward every visual property yourself; nothing is preserved automatically except what's outside the redaction rectangle.
- Redaction rectangles must be sized precisely to the span/line, not the whole block, or you risk deleting adjacent images/vector art (`images=`/`graphics=` flags mitigate but don't eliminate this risk).
- `insert_textbox`/`insert_htmlbox` give you wrapping/shrink-to-fit, but only within a single font/style per call — genuinely mixed-style runs (e.g., part-bold sentence) need multiple insert calls per original line.
- The alternative some PDF tools use — a pure visual overlay (paint white over old text, then draw new text on top, without ever calling `apply_redactions`) — is simpler and avoids `apply_redactions`'s risk of over-deleting graphics, but it is **not real removal**: the old text objects remain extractable in the content stream underneath (a real concern for a translation tool where leaving the original English text machine-readable under a visual patch is a data-hygiene/QA problem, not just a translation problem). The plan's own principle of deterministic reconstruction favors the redact+reinsert route despite the extra precision it demands, precisely because it truly deletes the old operators rather than just painting over them.

### 4. Important limitations to flag

- **Font flags** are documented as sometimes incorrect — never gate bold/italic decisions on `flags` alone (Section 3 above).
- **Image inventory** (`get_images`) can list referenced-but-not-displayed images; use `get_image_info()` for what's actually rendered (Section 4 above).
- **Rotation**: pages carry a `rotation` property plus `derotation_matrix`/`rotation_matrix` for converting between rotated-page and unrotated coordinate spaces — any geometry/text-fit math must pick one coordinate space consistently and not mix rotated/unrotated bboxes.
- **Redaction side effects on graphics**: `apply_redactions()`'s `images=`/`graphics=` parameters mean redacting a text rectangle is not guaranteed content-neutral to everything else on the page unless the rectangle is tightly scoped and the flags are chosen deliberately (Section 7 above).
- **CJK/Indic scripts**: `get_text_length()` explicitly supports "Base-14 or CJK" builtin fonts only for width measurement; for Indic scripts (Telugu, Devanagari, Tamil, Kannada — central to this project per master-plan Section 22) you must load the actual target `Font` (e.g. Noto Sans Telugu) and use `Font.text_length()`, not the module-level Base-14/CJK-only function. This was not separately re-verified beyond the `get_text_length` doc's own "Base 14 Font or CJK font name" wording — treat "does `Font.text_length()` correctly shape/measure complex Indic conjuncts" as still requiring an empirical check against real Devanagari/Telugu strings before relying on it, since text shaping (ligatures, reordering) for Indic scripts is a font-rendering-engine concern that the docs fetched here did not explicitly confirm PyMuPDF handles correctly for width measurement.
- **Embedded font extraction limits**: PyMuPDF can read embedded font programs (for e.g. re-embedding or fallback decisions) but the fetched docs did not surface a documented guarantee that every embedded font subset can be fully round-tripped (subsetted fonts often only contain the glyphs actually used in the source document, which is irrelevant for extraction of the *original* text but directly relevant if you ever wanted to reuse the *original* embedded font to render *new* translated glyphs it was never subsetted to contain — reinforcing why Section 22's language-aware fallback font table, e.g. Noto Sans Telugu, is necessary rather than optional).

---

## Limitations of this research pass

- WebFetch returns a summarized/condensed version of each page (via a small model), not the raw HTML/text — so exact verbatim signatures (default parameter values, full parameter lists) should be spot-checked against the live docs page before being hard-coded into code comments or docstrings, especially for `insert_text`/`insert_textbox`, which have more parameters than shown here.
- The official PyMuPDF **recipes/how-to page for redaction specifically** could not be located at a stable URL during this pass (a fetch to `recipes-text.html#how-to-redact-and-strike-out-text` returned "not found in this page's visible content"); the redact+reinsert pattern above is corroborated by the general FAQ and Page-class docs plus a linked official GitHub Discussion, not a single canonical "how-to" page — flagged as a slightly lower-confidence synthesis of multiple official-repo/doc sources rather than one authoritative paragraph.
- Indic-script shaping/measurement correctness (noted above) is an open verification item for the OCR/font-fallback milestone, not something these docs settled.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| PyMuPDF | PyPI project page | https://pypi.org/project/PyMuPDF/ | Official package index | 2026-09-08 | 1.28.2 (2026-08-06) | Current version, license (AGPL/commercial dual), Python >=3.10 |
| PyMuPDF | GitHub Releases | https://github.com/pymupdf/PyMuPDF/releases | Official GitHub repo | 2026-09-08 | 1.28.2 | Confirms 1.28.2 built on MuPDF 1.28.0; release history |
| PyMuPDF | TextPage docs | https://pymupdf.readthedocs.io/en/latest/textpage.html | Official docs | 2026-09-08 | latest | get_text() modes; font flags "not necessarily correct" warning |
| PyMuPDF | Appendix 1 (extractDICT structure) | https://pymupdf.readthedocs.io/en/latest/app1.html | Official docs | 2026-09-08 | latest | block/line/span/char dict structure and bbox nesting |
| PyMuPDF | Page class docs | https://pymupdf.readthedocs.io/en/latest/page.html | Official docs | 2026-09-08 | latest | apply_redactions, add_redact_annot, insert_text/textbox/htmlbox, get_images/get_image_rects/get_drawings/get_pixmap, rotation/derotation_matrix, annots() |
| PyMuPDF | Document class docs | https://pymupdf.readthedocs.io/en/latest/document.html | Official docs | 2026-09-08 | latest | extract_image, xref_object/xref_get_keys/xref_get_key/xref_stream_raw; get_images() "not actually displayed" caveat |
| PyMuPDF | functions.html (get_text_length) | https://pymupdf.readthedocs.io/en/latest/functions.html | Official docs | 2026-09-08 | latest | get_text_length signature, Base-14/CJK-only limitation |
| PyMuPDF | Font class docs | https://pymupdf.readthedocs.io/en/latest/font.html | Official docs | 2026-09-08 | latest | Font.text_length works for any loaded font incl. custom; fallback-font substitution behavior |
| PyMuPDF | FAQ | https://pymupdf.readthedocs.io/en/latest/faq/index.html | Official docs | 2026-09-08 | latest | redact+reinsert pattern, insert_textbox fit-check pattern, sort=True reading-order caveat |
| PyMuPDF | GitHub Discussion #3422 | https://github.com/pymupdf/PyMuPDF/discussions/3422 | Official issue tracker/discussion | 2026-09-08 | n/a | Community-confirmed redact+insert_textbox text-replacement pattern, reading-order fix-up |
