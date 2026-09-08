# PDF Internal Structure — Technical Research

Date checked: 2026-09-08

This file covers general PDF-format facts (independent of any library), then
cross-references each one against Part A's PyMuPDF findings
(`docs/research/pymupdf.md`) to make explicit what PyMuPDF exposes vs. what it
does not — the goal being to never confuse "what the page looks like" with
"what the PDF actually, structurally, contains."

Primary source note: the authoritative normative source is **ISO 32000-2:2020
(PDF 2.0)**, free-to-download via the PDF Association
(https://pdfa.org/resource/iso-32000-2/), and its predecessor **ISO
32000-1:2008 / Adobe PDF 1.7 Reference (PDF32000_2008)**
(https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf).
Both spec PDFs exceeded this session's fetch tooling size limit (>10MB), so
this research falls back to a mix of (a) the PDF Association's own summaries
and search-indexed section references, (b) Wikipedia's PDF article as a
general/secondary technical source, and (c) W3C WCAG PDF techniques for the
reading-order material — **all explicitly lower-confidence tier-4/6/7
sources per the technical-research skill's priority list**, used only
because the tier-1 spec document itself could not be fetched in full this
session. Anything load-bearing for implementation should be re-verified
against the actual ISO 32000-2 text (or MuPDF/PyMuPDF's own source, which
implements the spec) before being hard-coded into parsing logic.

---

## 1. Text objects and operators

A PDF page's visible content is a **content stream**: a sequence of
stack-based, PostScript-like operators (not an executable program — no
loops/conditionals), interpreted top-to-bottom. Text is drawn inside explicit
`BT` (begin text) / `ET` (end text) object blocks using operators such as
`Tj` (show a string) and `TJ` (show an array of strings interleaved with
positioning adjustments, used for kerning). (Source: general PDF structure —
Wikipedia PDF article, https://en.wikipedia.org/wiki/PDF, fetched 2026-09-08;
operator names corroborated by search results referencing ISO 32000-2's
content-stream operator table, https://www.iso.org/obp/ui/#iso:std:iso:32000:-2:ed-1:v1:en.)

**PyMuPDF exposure**: PyMuPDF does not hand you raw `Tj`/`TJ` operators
directly through the high-level API — it parses the content stream for you
and returns decoded spans/lines/blocks via `get_text()`. The raw operators
are reachable only via the low-level `Document.xref_stream_raw(xref)` on the
page's content-stream xref (docs/research/pymupdf.md, Section 11), which
returns the undecoded stream bytes for manual parsing if ever needed.

## 2. Fonts — embedded vs. referenced, font programs

A PDF font dictionary either (a) references one of the 14 standard fonts by
name, expecting the viewer to supply/substitute a matching font, or (b)
embeds an actual font program (Type 1, TrueType, or OpenType/CFF) as a stream
object (`FontFile`/`FontFile2`/`FontFile3`), guaranteeing consistent
rendering regardless of what's installed on the viewing machine. Embedded
fonts are frequently **subsetted** — containing only the glyphs the source
document actually used — for size reasons. (Source: Wikipedia PDF article,
fetched 2026-09-08; general PDF font-embedding practice.)

**PyMuPDF exposure**: `get_text()` span dicts give you the font's *name*
string, `size`, `flags`, and `color` (docs/research/pymupdf.md Section 2–3),
but the flags are documented as unreliable. Whether a given font is embedded,
and its actual program bytes, are reachable via the xref-level API
(`xref_object`, `xref_get_keys`) rather than through `get_text()` — i.e.
"is this font embedded, and with which glyphs" is a **structural** fact
PyMuPDF can answer, but only by dropping to the xref layer, not from
`get_text()` output alone.

## 3. Glyphs vs. characters — ToUnicode CMaps

A PDF's text operators show **character codes**, and a code is mapped to a
**glyph** by the font's internal encoding — these codes do not have to be
Unicode or even ASCII. To recover the actual semantic character (e.g., for
copy/paste or search), the font dictionary can carry an optional
**`ToUnicode` CMap** stream, defined in the PDF spec's text/font section,
which maps character codes to Unicode code points. If a PDF was generated
without a valid `ToUnicode` map (common for poorly-generated or
maliciously-obfuscated PDFs, and for some CJK/complex-script producers),
there is **no reliable way to recover the actual character** — the codes are
only guaranteed to map correctly to *glyphs* (for correct visual rendering),
not to *characters* (for correct text extraction). (Sources: search results
on ToUnicode CMaps referencing PDF spec §9.10.3, and the PyMuPDF issue
tracker discussion of ToUnicode editing —
https://github.com/pymupdf/PyMuPDF/issues/530, fetched 2026-09-08 —
confirming this is a live, real-world extraction failure mode, not a
theoretical one.)

**PyMuPDF exposure**: `get_text()` relies on the font's encoding/ToUnicode
data to decode text; when ToUnicode is missing or wrong, PyMuPDF's extracted
text can be silently wrong (garbled characters) with no error raised — this
is a documented-by-community (not doc-page-stated) risk relevant to the
master plan's "PDF rule" (never assume visual appearance = structure) and
to the `pdf-forensics` skill's purpose. Treat any extracted text as
suspect until spot-checked against the rendered page for documents from
unknown/older producers.

## 4. Character positioning — text matrices, kerning

Each text-showing operation is positioned via the current **text matrix
(Tm)**, plus text-state parameters: character spacing (`Tc`), word spacing
(`Tw`), horizontal scaling (`Tz`), leading (`TL`), and rise (`Ts`). The `TJ`
operator additionally allows small per-glyph position adjustments inline
(effectively manual kerning) without altering the text matrix. (Source:
search results citing ISO 32000-2's text-state-parameters/operators table;
Wikipedia PDF article's summary of the content-stream model.)

**PyMuPDF exposure**: PyMuPDF resolves all of this into a final **glyph
origin** (`origin: (x, y)`) and **bounding box** per span/char
(docs/research/pymupdf.md Section 2) — i.e. it gives you the *result* of
applying `Tm`/`Tc`/`Tw`/`Tz`/`TJ` adjustments (a pixel/point-space
coordinate), not the underlying operator parameters themselves. This is
sufficient for layout-preserving reconstruction (which only needs "where did
this glyph end up") but not for literally reproducing the source's exact
`Tc`/`Tw` values if you wanted to re-emit byte-identical content-stream
operators.

## 5. Text spans

"Span" in the PyMuPDF sense (a run of characters sharing one font/size/color)
is **not itself a PDF-format primitive** — the PDF spec has no object called
a "span." It's PyMuPDF's own extraction-time grouping of adjacent characters
that share identical graphics-state properties (Source: inferred from the
structure documented in docs/research/pymupdf.md Section 2 — the dict-mode
output groups chars into spans by shared style, matching how MuPDF's text
extraction is commonly described). This matters because "span boundary" is
an artifact of the extraction algorithm's grouping heuristic, not a hard
boundary the original PDF author drew — two visually-adjacent runs that
happen to share identical style could be merged into one span, or a single
semantic word could be split into two spans if the PDF producer emitted it
as two separate `Tj` calls with a font-state change in between (e.g. one
subtly different embedded font subset).

## 6. Images — raster vs. vector

Raster images are **Image XObjects**: dictionary + stream objects holding
compressed pixel data (`DCTDecode` for JPEG, `FlateDecode` for lossless,
`JPXDecode` for JPEG2000, etc.), placed on the page via the `Do` operator
inside a coordinate transform. Small inline raster images can alternatively
be embedded directly in the content stream as **inline images** (`BI`/`ID`/
`EI` operators) rather than as separate XObjects. (Source: Wikipedia PDF
article; corroborated generally by PDF spec references to Image XObjects in
search results.)

**PyMuPDF exposure**: `Page.get_images()` / `extract_image(xref)` handle the
XObject case (docs/research/pymupdf.md Section 4); whether PyMuPDF's
`get_images()` also surfaces inline images was **not confirmed** in this
research pass — this should be verified empirically (or against the docs
directly) before assuming inline images are captured by the same code path,
since the docs excerpt fetched did not explicitly address inline images.

## 7. Vector drawings and clipping paths

Vector graphics are built from **path-construction operators** (`m`
moveto, `l` lineto, `c`/`v`/`y` Bézier curves, `re` rectangle) followed by a
painting operator (`S` stroke, `f`/`f*` fill, `B` fill+stroke) or a
**clipping** operator (`W`/`W*`, which doesn't paint anything itself but
marks the current path as the new clipping boundary for subsequent
painting, taking effect after the next path-painting operator).
(Source: general PDF content-stream operator naming referenced in search
results tied to ISO 32000-2's operator summary table.)

**PyMuPDF exposure**: `Page.get_drawings()` reconstructs these paths into
Python-friendly dicts (`items`, `fill`, `color`, `width`, `closePath`, `rect`
— docs/research/pymupdf.md Section 5). Whether `get_drawings()` also
surfaces active clipping-path state (as opposed to just paint operations)
was **not directly confirmed** in this pass; a text-replacement pipeline
that inserts new content into a region that was clipped in the original
should verify clip behavior empirically rather than assume `get_drawings()`
enumerates clip regions the same way it enumerates painted shapes.

## 8. Transparency and blend modes

PDF 1.4+ supports alpha compositing, blend modes (multiply, screen, etc.),
and **transparency groups** (a sub-content-stream composited as a unit before
being blended into the page), all designed to degrade gracefully in older
viewers that don't support them. (Source: Wikipedia PDF article, fetched
2026-09-08.)

**PyMuPDF exposure**: span/drawing dicts don't appear to carry blend-mode
data in the fetched docs excerpts (opacity does appear on `insert_htmlbox`
as a parameter you can *set*, docs/research/pymupdf.md Section 8, but that's
for newly-inserted content, not extracted-from-source blend-mode
introspection). `get_pixmap()` rendering does respect transparency/blend
modes when rasterizing (it's a real renderer), so **visual QA via pixmap
diffing will correctly reflect transparency effects even though the
structured extraction API may not expose blend-mode as a discrete,
inspectable field** — this is exactly why the master plan pairs
`get_drawings()`/`get_text()` structural extraction with `get_pixmap()`
visual QA rather than relying on structural extraction alone (Section 36–37
of the master plan).

## 9. Optional Content Groups (layers)

Since PDF 1.5, content can be tagged as belonging to an **Optional Content
Group (OCG)**, letting a viewer show/hide that content (e.g. a
multi-language document where each language's text is a separate OCG layer,
or CAD-style layer toggles), per ISO 32000 §8.11 "Optional Content."
(Source: search results referencing ISO 32000 §8.11 and Adobe SDK OCG API
docs, https://opensource.adobe.com/dc-acrobat-sdk-docs/pdflsdk/apireference/PD_Layer/PDOCG.html,
fetched 2026-09-08.)

**This is directly relevant and easy to get wrong for a translation tool**:
if a source PDF already uses OCGs to hold multiple language layers (not
uncommon for bilingual official documents), naive text extraction via
`get_text()` may pull text from a *hidden* layer as if it were visible page
content, or conversely a translation pipeline might not realize some
"page text" is conditionally invisible. `get_text()`'s dict/rawdict output,
per the fetched docs, does not appear to carry an explicit
"is this span currently visible per OCG state" flag — checking OCG
visibility, if relevant to a given document, would require the xref-level
API (`Document.xref_get_keys`/`xref_get_key` against the page's
`/Properties`/`/OCProperties`) rather than the high-level `get_text()` call.
**Flagged as an unverified gap**: confirm with real bilingual/OCG-bearing
PDFs before assuming `get_text()` is layer-aware.

## 10. Why "reading order" is not a native PDF concept

The physical order of operators in a content stream reflects **how the PDF
producer happened to draw things**, which very often does not match the
order a human would read them in (e.g. a two-column layout, or a PDF
generator that emits headers/footers before/after body text arbitrarily).
The PDF spec's answer to this is **Tagged PDF**: an optional logical
**structure tree**, rooted at `StructTreeRoot` in the document catalog, that
explicitly encodes parent/child reading-order relationships as a separate
data structure layered *on top of* the content stream — it is optional, and
most PDFs (especially ones produced by non-authoring-tool pipelines, or
older documents) do not have one. Where no structure tree exists, "reading
order" must be **inferred from geometry** (column detection, top-to-bottom/
left-to-right heuristics), which is inherently heuristic and imperfect.
(Sources: PDF Association / W3C WCAG PDF techniques,
https://www.w3.org/TR/WCAG20-TECHS/PDF3.html, and general Tagged-PDF
structure summaries surfaced in search results, fetched 2026-09-08.)

**PyMuPDF exposure**: `get_text(sort=True)` offers a **positional**
top-left-to-bottom-right heuristic sort (confirmed via the PyMuPDF FAQ,
docs/research/pymupdf.md Section 1/7) — explicitly documented by PyMuPDF's
own FAQ as imperfect for multi-column layouts, requiring the caller to
identify column boundaries manually. PyMuPDF's `get_text()` does **not**
read/expose a document's Tagged-PDF `StructTreeRoot` logical structure tree
in the API surface covered by this research pass — this was not found in
any of the fetched pages, and should be treated as **not supported by the
high-level API** unless a dedicated method is found in a follow-up check
(worth a targeted look before the "reading order inference" milestone,
since if a source PDF *is* tagged, that's a strictly better reading-order
signal than positional heuristics, and it would be a shame to build a purely
geometric reading-order inferencer if PyMuPDF can already read the tag tree
for tagged PDFs). **This is flagged as an open item, not a settled fact.**
This directly confirms the master-plan's implicit assumption (Section 5's
"reading_order[]" as a field the *document model* must construct, not
something extracted verbatim) — a "paragraph" or "reading order" is squarely
something this project's own inference layer must build, not a PyMuPDF or
even base-PDF-format guarantee.

---

## Summary table — structural fact vs. PyMuPDF exposure

| PDF concept | Native to PDF format? | Exposed by PyMuPDF's high-level API? |
|---|---|---|
| Content-stream text operators (Tj/TJ/Tm) | Yes | Not directly — resolved into span origin/bbox; raw stream via `xref_stream_raw` only |
| Embedded vs. referenced fonts | Yes | Font *name* yes; embedded-or-not / font program needs xref-level API |
| ToUnicode (char identity) | Yes, optional | Used internally by `get_text()`; no explicit "ToUnicode present?" flag surfaced in docs checked |
| Character position (Tm/Tc/Tw/Tz) | Yes | Resolved into final origin/bbox, not raw params |
| "Span" (style-uniform run) | No — extraction artifact | Yes, this is PyMuPDF's own grouping unit |
| Raster images (XObject) | Yes | Yes (`get_images`/`extract_image`), with the "not actually displayed" caveat |
| Inline images (BI/ID/EI) | Yes | Not confirmed in this pass — verify |
| Vector paths / clipping | Yes | Paths via `get_drawings()`; clip-state exposure not confirmed |
| Transparency / blend modes | Yes | Not exposed as inspectable extracted field; reflected correctly in `get_pixmap()` rendering |
| Optional Content Groups (layers) | Yes | Not confirmed as reflected in `get_text()` visibility; needs xref-level check |
| Reading order / paragraphs / structure tree | Only if Tagged PDF (optional) | Positional heuristic sort only (`sort=True`); StructTreeRoot access not confirmed |

---

## Limitations of this research pass

- The primary tier-1 source (ISO 32000-2 / PDF32000_2008 full spec PDF) could
  not be fetched directly — it exceeded the 10MB WebFetch content-length
  limit in this environment. All operator-level claims (Tj/TJ/Tm/Tc/Tw/Tz,
  W/W* clipping, `re`/`m`/`l`/`c` path construction) rest on
  search-engine-surfaced secondary summaries and Wikipedia rather than a
  direct quote from the spec text itself. These are extremely
  well-established, uncontroversial facts about the PDF format (consistent
  across every secondary source checked), but per the technical-research
  skill's rule, this is flagged explicitly as tier-4/6 sourcing rather than
  tier-1, and should be treated as "very likely correct, not independently
  spec-verified this session."
- Several PyMuPDF-specific "does the high-level API expose X" questions
  (inline images, clip-path enumeration, OCG visibility flags, StructTreeRoot
  access) came back as **not confirmed either way** rather than confirmed
  absent — these are explicit open items for a follow-up, narrower doc check
  before the relevant implementation milestone, not settled negatives.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| PDF format | ISO 32000-2:2020 standard listing | https://www.iso.org/obp/ui/#iso:std:iso:32000:-2:ed-1:v1:en | Official standards body | 2026-09-08 | ISO 32000-2:2020 | Confirms current PDF 2.0 spec identity/structure; full text not fetchable this session |
| PDF format | PDF Association — ISO 32000-2 resource page | https://pdfa.org/resource/iso-32000-2/ | Official standards organization | 2026-09-08 | ISO 32000-2:2020 | Free-download availability of the spec (fetch blocked by 403 in this session) |
| PDF format | Adobe/ISO PDF32000_2008 (PDF 1.7 base spec) | https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf | Official spec (Adobe-hosted) | 2026-09-08 | PDF32000_2008 (ISO 32000-1 base) | Attempted direct fetch; exceeded 10MB tool limit, not retrievable this session |
| PDF format | Wikipedia — Portable Document Format | https://en.wikipedia.org/wiki/PDF | Secondary/general (tier 6-7) | 2026-09-08 | n/a | Content-stream model, embedded vs. standard-14 fonts, XObjects, transparency, OCG, tagged-PDF summary |
| PDF format / ToUnicode | Search results on ToUnicode CMap spec (§9.10.3) | (aggregated search, no single canonical URL fetched) | Secondary/community (tier 6) | 2026-09-08 | n/a | ToUnicode CMap purpose and section reference |
| PyMuPDF | GitHub Issue #530 (ToUnicode editing) | https://github.com/pymupdf/PyMuPDF/issues/530 | Official issue tracker | 2026-09-08 | n/a | Confirms ToUnicode mapping problems are a real, encountered extraction failure mode |
| PDF format | W3C WCAG 2.0 Techniques — PDF3 (reading order) | https://www.w3.org/TR/WCAG20-TECHS/PDF3.html | Official W3C technique (accessibility) | 2026-09-08 | WCAG 2.0 | Tagged-PDF structure tree drives reading order, independent of content-stream order |
| PDF format | Adobe SDK — PDOCG API reference | https://opensource.adobe.com/dc-acrobat-sdk-docs/pdflsdk/apireference/PD_Layer/PDOCG.html | Official Adobe SDK docs | 2026-09-08 | n/a | Optional Content Group (OCG) object model reference, ISO 32000 §8.11 |
| PyMuPDF (cross-reference) | See docs/research/pymupdf.md Sources table | (internal cross-reference) | Official docs (already tabulated) | 2026-09-08 | 1.28.2 | Basis for all "PyMuPDF exposure" comparisons in this file |
