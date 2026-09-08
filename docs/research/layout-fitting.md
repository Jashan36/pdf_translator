# Layout Fitting — Research Findings

Scope: Section J. Practical methods for fitting translated text into
original PDF geometry while preserving layout, refining master plan
Sections 19–20.

Date checked: 2026-09-08.

---

## 1. Font-size reduction search strategy

The master plan (Section 19) already specifies a **linear step-down
search** (18 → 17.5 → 17 → ... → 15pt floor). This is simple and
predictable but does up to N/step_size measurement calls.

A **binary search** over the size range `[min_size, original_size]`
converges in O(log n) measurement calls instead of O(n), which matters
because each measurement call (`Font.text_length()` /
`insert_htmlbox` dry-run layout) is not free, especially once shaping
(HarfBuzz, via `insert_htmlbox`) is involved for Indic scripts —
shaping a string is more expensive than simple Latin advance-width
summation.

Recommendation: **binary search for the largest fitting size**, with
a small fixed final step (e.g. round to nearest 0.5pt) to match the
master plan's granularity and avoid float noise causing visually
inconsistent sizes across similar blocks. This is a refinement of
Section 19, not a contradiction — same tolerance/floor semantics,
fewer measurement calls.

Text measurement API (verified against official PyMuPDF docs):
`Font.text_length(text, fontsize)` returns the width in points for a
loaded `pymupdf.Font`, and per PyMuPDF's own discussion (#1915),
`fitz.get_text_length()` is the legacy, Base-14-only function and is
**not recommended** — `Font.text_length()` is current and supports
fallback-font-aware measurement (source: pymupdf.readthedocs.io/en/latest/font.html,
GitHub Discussion #1915). Because `Font.text_length()` measures
**advance widths of a font**, not full HarfBuzz-shaped layout, it is
an approximation for Indic scripts (conjuncts/reordering can change
effective width vs. naive character-width summation) — for final
verification, measure the actual `insert_htmlbox` output geometry
(e.g. via a dry-run render or the Story's reported layout height/
overflow) rather than trusting `text_length` alone when precision
matters at the fit boundary.

## 2. Line-height / leading adjustment

Reducing line spacing (leading) between the font's default and a
documented minimum (e.g. down to ~0.9–1.0x of the font's nominal
line height) is a standard, safe secondary lever after font-size
reduction, used before resorting to wrapping into more lines or
expanding the box. It should be applied only after font-size search
fails at the floor size, per master plan Section 19 Step 3→4
ordering — same idea, adding leading adjustment as an intermediate
step between size-reduction and box/wrap changes.

## 3. Horizontal scaling (condensing) — why it's riskier for Indic scripts

General typesetting knowledge: horizontal scaling (non-uniform
scaling of glyph advance widths, e.g. PDF `Tz` horizontal-scale
operator, or condensed-style faux transforms) is already considered
poor typographic practice for Latin text (it distorts stroke
proportions), but is explicitly worse for complex scripts.

Verified technical reasoning (tier: HarfBuzz/OpenType shaping
documentation, general secondary sources — the exact phrase
"horizontal scaling breaks Indic shaping" was not found verbatim in
an official doc, so this is a reasoned extension of primary sourcing,
flagged as such):

- Indic-script rendering depends on **GPOS-driven mark positioning**
  and ligature/conjunct substitution computed by the shaper
  (HarfBuzz) **for the font's actual glyph metrics at shape time**
  (harfbuzz.github.io/what-is-harfbuzz.html: HarfBuzz "selects and
  positions the corresponding glyphs ... applying all of the
  necessary layout rules and font features"). Applying a uniform or
  non-uniform post-hoc horizontal scale to already-shaped glyph
  positions/advances (rather than re-shaping at a different point
  size) does not re-run GPOS — it just stretches/compresses positions
  that were computed for the original metrics, which can misalign
  combining marks, vowel signs, and conjunct components relative to
  their base consonants.
- OpenType shaping documentation (n8willis/opentype-shaping-documents,
  a widely used technical reference for Indic OpenType shaping) notes
  Indic scripts require careful two-dimensional glyph placement
  around base consonants; this is inherently more fragile under naive
  geometric transforms than simple Latin kerning-only layout.
- **Conclusion for this project:** horizontal scaling must be treated
  as **opt-in / last resort with an explicit warning**, not a default
  safe lever, and should never be applied to Indic-script spans routed
  through `insert_htmlbox`'s shaped output — prefer re-shaping at a
  smaller font size (Section 1 above) or wrapping (Section 4) instead.
  For Latin-only spans it is a much smaller risk and can be a
  secondary lever, still with a warning since it's a known
  typographic compromise.

## 4. Word wrapping / paragraph reflow

`insert_htmlbox()` is HTML/CSS-based and inherits standard block/text
CSS reflow behavior (it lays out via PyMuPDF's `Story`/HTML engine),
so wrapping within a fixed-width `<div>`-equivalent box is a built-in
capability of the chosen rendering path rather than something to
reimplement — this reduces engineering risk versus building a custom
line-breaking algorithm. (Confirmed generally by the Artifex blog:
insert_htmlbox "internally us[es] a Story object to layout the
content" with HTML/CSS support — pymupdf.readthedocs the exact
line-breaking algorithm used internally was not independently
verified beyond "Story"/HTML box layout; treat internal line-breaking
implementation details as unverified specifics, but the capability
itself — HTML text reflow in a box — is documented.)

Recommendation: wrapping is the master plan's Step 4 (after font-size
reduction fails) and should rely on `insert_htmlbox`'s own reflow
rather than a hand-rolled line breaker, consistent with "verify the
official API before implementing it yourself."

## 5. When bounding-box expansion is safe vs unsafe

This is a **collision/geometry** question, not a typography-tool
question, so it draws on the master plan's own stated objective
(Section 20: "text does not overlap protected objects", "text remains
inside its intended region").

Safe-by-default expansion:
- Expanding into **whitespace already verified empty** in the
  original page's rendered content stream / object map (no other
  text span, image, vector object, or annotation occupies that area)
  up to some small margin (e.g. a few points), verified via geometry
  extraction (see below), not assumption.
- Expanding **vertically inside the same column/paragraph** when the
  block is the last one on the page or followed by known continuation
  space, since vertical expansion within reading flow rarely collides
  with unrelated content if collision-checked first.

Unsafe / needs explicit opt-in and a warning:
- Expanding **outside the original text block's original margins**
  into a page margin or gutter, since this changes the page's overall
  visual balance even if it doesn't collide with an object.
  (This matches Section 20's Eg/geometry-deviation penalty concept —
  expansion should cost something in the objective function, not be
  free.)
- Any expansion that has **not** been collision-checked against
  neighboring text/images (see below) — never expand blind.
- Horizontal expansion across a multi-column boundary.

## 6. Collision detection approach

Recommended approach, built entirely on primary PyMuPDF geometry APIs
(verified: `page.get_text("dict")` returns block/line/span bounding
boxes in points, and images/objects are enumerable via the same
extraction — pymupdf.readthedocs.io/en/latest/app1.html,
recipes-text.html):

1. Extract all block/line/span bounding boxes and image bounding
   boxes for the page **once**, before any fitting decision (single
   source of truth — matches the "PDF metadata + visual inspection"
   guidance in master plan Section 21).
2. Build a simple 2D rectangle index (even a flat list is fine at
   page scale — a few hundred objects) of all "protected" rectangles:
   every span/image bbox **other than** the block currently being
   fitted.
3. For a candidate expanded bbox, test axis-aligned rectangle
   intersection (`not (a.x1 <= b.x0 or a.x0 >= b.x1 or a.y1 <= b.y0
   or a.y0 >= b.y1)`) against every protected rectangle; reject
   (or shrink to the nearest non-colliding size) if any intersect.
4. Treat this check as mandatory before accepting any bounding-box
   expansion (Section 5's "safe" category is conditional on this
   check passing, not on the category alone).

This is standard axis-aligned bounding-box (AABB) collision detection
— general/verified-safe programming technique, not tool-specific, so
no citation risk here; the only tool-specific part (bbox source) is
cited to PyMuPDF's own extraction docs above.

---

## Recommended algorithm (concrete, refines master plan Section 19–20)

```text
for each translated block:
    1. Extract original bbox, font, size, protected-rectangle index (once per page).
    2. Binary-search font size in [floor_size, original_size]:
         - shape/measure candidate text at mid-size via Font.text_length()
           (fast filter) THEN confirm with insert_htmlbox dry-layout for
           Indic spans near the fit boundary (HarfBuzz-shaped width may
           differ from naive advance-width sum).
         - narrow range based on fits/doesn't fit.
       -> if a fitting size >= floor_size found: use largest such size, done.
    3. If floor_size still doesn't fit:
         a. Reduce line-height toward documented minimum (~0.9-1.0x), retry fit.
    4. If still doesn't fit:
         a. Allow controlled wrapping via insert_htmlbox's own reflow
            inside the existing box width.
    5. If still doesn't fit:
         a. Check bounding-box expansion candidates against the
            protected-rectangle collision index (see Section 6).
         b. If a non-colliding expansion exists within a small margin
            policy: expand, log as a soft warning (geometry deviation
            cost per Section 20's Eg term).
         c. If expansion would collide, or exceeds margin policy: do NOT
            expand automatically.
    6. Horizontal scaling: NEVER auto-applied to Indic-script spans.
       For Latin-only spans, allow only as an explicit opt-in with a
       recorded warning, after all of steps 2-5 fail.
    7. If nothing above fits: mark LAYOUT_WARNING, surface for human
       review (per Section 19 Step 5) — never silently clip or silently
       force an unsafe expansion/scale.
```

Safe by default: font-size binary search, line-height reduction,
`insert_htmlbox` wrapping, collision-checked small expansions.
Needs explicit opt-in + warning: any bbox expansion beyond a small
margin or across original block/column margins, and all horizontal
scaling (especially for Indic scripts, where it should be avoided
entirely rather than merely warned about).

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| PyMuPDF | Font class docs | https://pymupdf.readthedocs.io/en/latest/font.html | Official docs | 2026-09-08 | current | `Font.text_length(text, fontsize)` is the current text-measurement API |
| PyMuPDF | "How do I measure text length with TextWriter? (get_text_length not recommended)" | https://github.com/pymupdf/PyMuPDF/discussions/1915 | Official GitHub repo | 2026-09-08 | current | `fitz.get_text_length()` is legacy/Base-14-only; `Font.text_length()` is preferred and fallback-font aware |
| PyMuPDF | Mastering PDF Text with PyMuPDF's `insert_htmlbox` | https://artifex.com/blog/mastering-pdf-text-with-pymupdfs-insert-htmlbox-what-you-need-to-know | Official vendor blog | 2026-09-08 | v1.23.8+ | insert_htmlbox does HTML/CSS-based layout via a Story object (implies built-in reflow/wrapping) |
| PyMuPDF | Appendix 1: Details on Text Extraction | https://pymupdf.readthedocs.io/en/latest/app1.html | Official docs | 2026-09-08 | current | `get_text("dict")` provides block/line/span bounding boxes for geometry/collision extraction |
| HarfBuzz | What is HarfBuzz? | https://harfbuzz.github.io/what-is-harfbuzz.html | Official project docs | 2026-09-08 | current | Shaper computes glyph selection/position from font+text — basis for why post-hoc horizontal scaling of shaped output is risky |
| OpenType shaping docs (community/technical reference) | Indic script shaping in OpenType | https://github.com/n8willis/opentype-shaping-documents/blob/master/opentype-shaping-indic-general.md | Community technical reference (lower tier — no official Microsoft/Adobe/Unicode doc found stating the scaling risk verbatim) | 2026-09-08 | current | Describes 2D glyph placement complexity around Indic base consonants, supporting (by extension) the risk of geometric post-processing |
