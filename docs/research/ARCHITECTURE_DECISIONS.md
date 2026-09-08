# Architecture Decisions

Synthesized from the research in `docs/research/*.md` (each cited
independently — see `SOURCES.md` for the aggregated list). Per the
research brief: this treats `PROJECT_STATE.md`'s architecture as a
hypothesis, not a conclusion — two decisions below (5 and 7) change or
sharpen it materially, and are called out.

---

## 1. PDF extraction engine

**Decision:** PyMuPDF, unchanged.

**Evidence:** `pymupdf.md`, `pdf-internals.md`. PyMuPDF exposes
block/line/span-level bbox, font name/size/flags, color, images
(`get_images`/`get_image_rects`), vector drawings (`get_drawings`),
and page rendering (`get_pixmap`) — everything the master plan's
Section 4.2/17/18 extraction needs. No alternative (pdfplumber,
pikepdf, Docling) was found to offer something PyMuPDF lacks for pure
extraction.

**Alternatives:** pikepdf (lower-level, no span/font convenience
layer), pdfplumber (no rendering/insertion path), Docling (see
Decision 3 — understanding layer, not extraction primitive).

**Why selected:** Already proven working in Milestone 1
(`core/pdf/analyzer.py`, 4 passing tests). Confirmed by fresh research
against current docs (v1.28.2), not just because it was already
chosen.

**Why alternatives rejected:** None offer span-level geometry +
rendering + insertion in one library with this project's required
fidelity.

**Risks:** Font `flags` metadata can be wrong/incomplete (documented
by PyMuPDF itself) — already mitigated in `_font_from_span` via a
font-name substring fallback. No confirmed high-level API for
Tagged-PDF/StructTreeRoot reading order — most real-world PDFs lack
Tagged-PDF data anyway, so this doesn't change the plan (Section 17's
"third pass: infer semantic groups" already assumes we must infer
order, not read it).

**Future replacement path:** None currently justified. Revisit only if
a future PDF sample exposes a concrete PyMuPDF extraction gap.

---

## 2. OCR engine

**Decision:** Do not add now. When Phase 7 (OCR) is reached: PaddleOCR
(PP-OCRv5/v6) primary, EasyOCR as a secondary path specifically for
Kannada.

**Evidence:** `ocr.md`. PaddleOCR is confirmed on v3.x (latest tagged
v3.7.0), and PP-OCRv5/v6/PaddleOCR-VL/PP-StructureV3 are all real,
currently-shipping components (verified against the official repo and
PaddleOCR-VL's HF model card) — the API has genuinely changed from 2.x
(`.predict()` replacing `.ocr(img, cls=True)`), confirming the user's
warning about stale tutorials was warranted.

**Critical gap found:** PaddleOCR's recognition models do **not**
cover Kannada or Malayalam — only Telugu, Hindi (Devanagari), and
Tamil among this project's target languages. EasyOCR was checked as a
secondary source and does cover Kannada; **no engine checked in this
pass (PaddleOCR, EasyOCR, docTR) covers Malayalam** — flagged as an
open risk (see `EXPERIMENTS.md`).

**Alternatives:** docTR (Apache-2.0, checked, no Malayalam either),
EasyOCR (covers Kannada, weaker general accuracy per its own
reputation — not benchmarked here).

**Why selected:** Matches master plan Section 15/48 (OCR only for
Class B/scanned PDFs, strictly after native-text PDFs work). Not
needed for Milestone 1-6.

**Why alternatives rejected:** Not rejected — EasyOCR is a required
secondary engine for Kannada coverage, not a discarded alternative.

**Risks:** Malayalam has no confirmed OCR path among the three engines
checked. If Malayalam scanned-PDF support is a hard requirement, this
needs dedicated research before Phase 7, not just picking whichever
engine is already integrated.

**Future replacement path:** Re-evaluate PaddleOCR-VL and
PP-StructureV3 (both confirmed real and current) for combined OCR +
layout/table detection once Phase 7/8 are reached — they may reduce
the need for a separate Docling integration (see Decision 3).

---

## 3. Document parsing / structure engine

**Decision:** PyMuPDF remains primary for structure. Docling is an
**optional** structural analyzer for complex documents only (Phase 8),
not the primary parser and not added now.

**Evidence:** `document-parsing.md`. Docling (MIT-licensed, local
execution, `DoclingDocument` model with per-item bboxes + page
provenance per its own docs) is a legitimate option for complex
layout/table cases, but PyMuPDF gives exact native geometry with zero
inference error for documents this project's MVP targets (Section 41:
paragraph text, headings, lists, basic tables).

**Alternatives:** PP-StructureV3 (bundled with the PaddleOCR/PaddleX
stack — more naturally arrives alongside OCR in Phase 7, not before).

**Why selected:** Master plan Section 16 already scoped Docling this
way ("do not make Docling responsible for final PDF rendering... use
it as an optional document understanding layer"). Research confirms
this is still the right call, not just an artifact of the original
plan.

**Why alternatives rejected:** Docling as *primary* parser would add a
second source of truth for geometry alongside PyMuPDF's own extraction
— unnecessary complexity before a documented case exists where
PyMuPDF's own structure inference (Section 17) is insufficient.

**Risks:** Docling's exact bbox field names/schema were UNVERIFIED in
this pass (`docling-core` schema needs direct inspection at
implementation time, not assumed from a general description).

**Future replacement path:** If Phase 8 shows PyMuPDF-based
table/column detection is unreliable on real-world documents, adopt
Docling or PP-StructureV3 at that point — decision deferred, not
foreclosed.

---

## 4. Internal document model

**Decision:** Keep the existing Pydantic model (`core/models.py`)
unchanged in shape; this research did not surface a reason to change
its structure.

**Evidence:** Cross-cutting — every other research area (layout
fitting, translation architecture, visual QA) assumes the model's
existing fields (bbox, font, reading_order, translation_status, etc.)
are sufficient inputs. No research area identified a missing field.

**Alternatives:** Not applicable — this is a project-internal design,
not a library choice.

**Why selected:** Already implemented and tested (Milestone 1).

**Why alternatives rejected:** N/A.

**Risks:** None identified yet. Revisit if Milestone 2 (text
replacement) or Milestone 3 (text-fit) surface a genuine gap (e.g. a
field needed for HarfBuzz-shaped-width caching, per Decision 7).

**Future replacement path:** Extend (add fields) rather than replace,
consistent with the "earn complexity only when proven" principle.

---

## 5. Translation engine

**Decision:** IndicTrans2 remains the primary candidate for Indic
translation quality — **but two new risks must be resolved before
committing**: (a) IndicTransToolkit, required for the practical
HuggingFace inference path, is community-maintained (not an official
AI4Bharat repo) and explicitly not built/tested for Windows; (b)
translation quality is not uniform across target languages.

**Evidence:** `indictrans2.md`, `indictrans-toolkit.md`. Verified
language codes for all 5 target languages (`eng_Latn`, `hin_Deva`,
`tel_Telu`, `tam_Taml`, `kan_Knda`, `mal_Mlym`) directly from
AI4Bharat's official README. CTranslate2 conversion is officially
documented by AI4Bharat as a supported inference path (the most
promising route to usable CPU performance for a family-local-machine
use case), though no official CPU/RAM benchmarks exist. Per a
secondary source citing the official paper (arXiv:2305.16307),
Western Indo-Aryan languages (Hindi) outperform Dravidian languages
(Telugu, Tamil, Kannada) due to training-data imbalance — **do not
present Hindi and Telugu/Tamil/Kannada output as equal-quality to the
user.**

**This changes `PROJECT_STATE.md`:** the "translation provider"
open decision should explicitly flag the Windows-compatibility risk
and per-language quality variance as things to resolve (experiment or
ask the user) before implementation, not just "pick a provider later."
Updated below.

**Alternatives:** Google Cloud Translation (cloud, costs money, no
Windows-compat risk, but master plan Section 33 wants a no-subscription
free path available), Argos Translate (offline, lower quality, no
Indic-specific tuning), Gemini API (contextual mode only, not a
document-translation replacement).

**Why selected:** IndicTrans2 is purpose-built for Indic languages
with official benchmarks the general-purpose alternatives don't
publish per-language; CLAUDE.md's existing stance is now
evidence-backed, not just asserted.

**Why alternatives rejected:** Not rejected outright — the provider
abstraction (Section 10) keeps them available. Google Cloud Translation
remains the "Standard" mode default per Section 46; IndicTrans2 is the
higher-fidelity "Contextual"/offline path once the Windows-compat
question is resolved.

**Risks:** Windows incompatibility of IndicTransToolkit could force a
WSL2/Docker/Linux-host requirement for this specific feature — a real
deployment-complexity cost for a "family local tool." Per-language
quality variance means QA/visual-QA warnings should be more aggressive
for Telugu/Tamil/Kannada output than Hindi.

**Future replacement path:** If Windows incompatibility proves
blocking, fall back to Google Cloud Translation or Argos for a pure-Python,
no-WSL path, accepting lower Indic-specific quality.

---

## 6. Contextual reasoning engine

**Decision:** Qwen3 via Ollama, used for translation review/post-editing,
terminology extraction, semantic classification, and context
summarization — **never** as the primary translation engine and never
for PDF geometry/rendering decisions.

**Evidence:** `qwen3-ollama.md`. Confirmed current Ollama tags
(dense: `qwen3:0.6b`–`32b`; MoE: `qwen3:30b`/`235b`, plus `-2507`
refresh variants), Apache-2.0 license, and genuine multilingual
*coverage* claims (119 languages including Hindi/Telugu/Tamil/Kannada)
— but no benchmarked translation *quality* claim for those specific
pairs, which is why it stays out of the primary-translator role.
Ollama's structured-output (JSON schema) support is confirmed and
suits the semantic-classification and context-summarization roles.

**Alternatives:** A cloud LLM (Gemini, per Section 11) for the same
contextual role — rejected as default for privacy (Section 34) but
kept available as an opt-in per the provider abstraction.

**Why selected:** Matches CLAUDE.md's existing stance; this research
confirms rather than overturns it — good evidence discipline is
demonstrating the hypothesis survived scrutiny, not just restating it.

**Why alternatives rejected:** Making it the primary translator would
contradict the one piece of hard evidence available (no per-language
Indic translation benchmark from Qwen's own docs, vs. IndicTrans2's
published ones).

**Risks:** Model size/hardware tradeoff unresolved — needs an
experiment on target hardware (see `EXPERIMENTS.md`).

**Future replacement path:** Swap Qwen3 for a newer Ollama-hosted
model if one publishes better structured-output or multilingual
reasoning benchmarks; the provider abstraction should not hard-code
"qwen3" as a literal string anywhere translation-critical.

---

## 7. Typography / rendering approach

**Decision — changes the plan materially:** PyMuPDF's classic text
APIs (`insert_text`, `insert_textbox`, `TextWriter`) **cannot**
reliably render Indic scripts. All Indic-script text insertion must
use `page.insert_htmlbox()` (added PyMuPDF v1.23.8), which shapes text
via an internal HarfBuzz-backed `Story` object. This is a **go/no-go
finding**, not a refinement.

**Evidence:** `pdf-typography.md`. Direct, unambiguous statements from
PyMuPDF's own maintainers on their official GitHub repo (Discussion
#3568): "You can never write Devanagari text using any of the methods
insert_text, insert_textbox or TextWriter!" and "Please use
insert_htmlbox. This is the only way in PyMuPDF to write with text
shaping." Corroborated by Artifex's own official blog post describing
the classic APIs as "effectively unusable for Hindi, Bengali, Tamil
and more than 120 other languages." Root cause confirmed against the
Unicode Consortium's own spec (Ch. 12) and HarfBuzz's official docs:
Indic scripts require visual reordering (vowel signs before their base
consonant) and conjunct formation via virama — simple left-to-right
character-to-glyph insertion cannot produce this.

**Alternatives:** Manually integrating a HarfBuzz Python binding
(`uharfbuzz`) and inserting pre-shaped glyph IDs directly — rejected
as unnecessary extra complexity since PyMuPDF already ships an
HarfBuzz-backed path (`insert_htmlbox`).

**Why selected:** Native to the already-chosen PDF library; no new
dependency required, just a different (and now mandatory) API call for
any Indic-script text.

**Why alternatives rejected:** A manual HarfBuzz integration would
duplicate work PyMuPDF already does internally, at higher complexity
and higher risk of getting virama/reordering rules wrong.

**Risks:** Even `insert_htmlbox` "needs a font with correct OpenType
tables for the target script, or it can still fragment glyphs" per a
second official discussion (#3659) — font choice (Noto Sans/Serif per
script, confirmed available and OFL-1.1-licensed via the official
`notofonts` GitHub org) must be verified empirically per script, not
assumed correct by default. `Font.text_length()` (used for the
text-fit algorithm) measures naive glyph-advance width and may not
match `insert_htmlbox`'s actual HarfBuzz-shaped width for Indic text —
flagged as an experiment (see `EXPERIMENTS.md`), not assumed either
way.

**Future replacement path:** None needed unless `insert_htmlbox`
itself proves insufficient for a specific script/font combination
found during Milestone 3+ empirical testing.

**Action required:** Milestone 2 (exact text replacement) must be
scoped to prove out `insert_htmlbox` specifically for at least one
Indic script early, not defer this discovery to a later milestone —
this is now a foundational rendering-path decision, not a detail.

**UPDATE (2026-09-08) — experimentally confirmed, GO:** Ran
`docs/research/indic-rendering-proof.md`, testing
`insert_htmlbox` + Noto Sans fonts against Telugu, Hindi, Tamil, and
Kannada across word/sentence/paragraph/punctuation/numerals/mixed-script
cases (24 renders total). Result: **PASS** for Hindi, **PASS WITH
LIMITATIONS** for Telugu/Tamil/Kannada. Core shaping (conjuncts, vowel
reordering, ligatures, word-boundary wrapping, mixed-script runs) is
correct in all four languages — the go/no-go question this decision
raised is answered **yes**. One narrow, fully-isolated bug was found:
native-script digit codepoints (e.g. Tamil ௧௨௩௪௫) render as wrong
glyphs in Telugu/Tamil/Kannada (not Devanagari), traced specifically to
PyMuPDF's glyph-selection step during page-content generation — not
the font (glyph coverage and `unicode_to_glyph_name` both confirmed
correct), not shaping/HarfBuzz, not the HTML/CSS layer (reproduces
identically via plain `insert_text`), not general script shaping
(everything else in the same scripts rendered correctly). Mitigation:
render numerals in Western Arabic digits (already the dominant
real-world convention for this content type) rather than native-script
digit codepoints — no architecture change, no new dependency, no
rendering-library switch required.

**UPDATE (Milestone 2 implementation) — new finding, not covered by
the original rendering proof:** the rendering proof validated *visual*
shaping correctness only (does the glyph sequence look right when
rendered to an image). Building the Milestone 2 golden test fixture
surfaced a second, independent property that must also be verified:
**does the resulting PDF's text LAYER correctly round-trip back to the
original Unicode string via `page.get_text()`?** For `insert_htmlbox`,
the answer is **no** — direct testing (inserting a Telugu string via
`insert_htmlbox`, saving, reopening, and calling `get_text("text")`)
produced a corrupted string (one character came back as U+00C8 "È"
instead of the correct Telugu vowel-sign character), even though the
same content renders visually correctly as a pixmap. The identical
string inserted via plain `insert_text()` with a directly-loaded font
file (`fontfile=...`) round-tripped byte-exact through `get_text()`, so
this is specific to `insert_htmlbox`'s font subsetting/CMap generation,
not a general PyMuPDF limitation. This is a real tradeoff, not a
strict improvement: `insert_text` gives correct extractable text but
wrong visual shaping for conjuncts; `insert_htmlbox` gives correct
visual shaping but a corrupted text layer. **Practical consequence:** a
translated PDF produced via `insert_htmlbox` may look correct but be
wrong for copy-paste, search, and screen-reader/accessibility
purposes. This strengthens (does not contradict) Decision 9's
OCR-based visual-QA bridge check — text-layer-based verification of
translated content cannot be trusted post-`insert_htmlbox`, so QA must
rely on rendered-pixel/OCR verification, not `get_text()`, to confirm
translated content is correct. Also affected the Milestone 2 golden
test fixture's design: its Indic text blocks are built with
`insert_text`+`fontfile=` (byte-exact ground truth for extraction
testing), not `insert_htmlbox` — visual shaping quality was already
proven separately by the accepted rendering proof, so the fixture
optimizes for extraction-test correctness instead. Not researched
further here per explicit instruction not to repeat rendering research
— tracked as Experiment 1c in `docs/research/EXPERIMENTS.md`.

---

## 8. Layout fitting strategy

**Decision:** Binary-search font-size reduction (using
`Font.text_length()` as a fast filter, confirmed against actual
`insert_htmlbox` layout near the fit boundary) → line-height reduction
(~0.9–1.0×) → `insert_htmlbox`'s own HTML/CSS wrapping → collision-checked
bounding-box expansion (AABB test against all other page objects) →
horizontal scaling as an explicit **opt-in for Latin-only text only,
never auto-applied to Indic scripts** → `LAYOUT_WARNING` for human
review as the final fallback.

**Evidence:** `layout-fitting.md`, cross-referenced with Decision 7's
shaping finding. Horizontal scaling distorts GPOS-computed mark/conjunct
positions without re-shaping — a documented risk specific to complex
scripts, not present for Latin text, so it cannot be a
uniformly-applied fallback the way the master plan Section 19 implies
by default.

**Alternatives:** Linear step-down search (simpler, more calls to the
shaping engine — rejected as slower with no accuracy benefit over
binary search).

**Why selected:** Refines master plan Section 19-20 with a concrete,
evidence-based algorithm rather than leaving "search 18, 17.5, 17..."
as a vague linear sweep.

**Why alternatives rejected:** Linear search is strictly dominated by
binary search here (same correctness, more shaping calls).

**Risks:** `Font.text_length()` vs. actual shaped width discrepancy
(see Decision 7) means the binary search's fast filter needs a
correction pass — do not trust it alone for Indic text without
validating against real `insert_htmlbox` output during Milestone 3.

**Future replacement path:** None anticipated; this is an algorithm
choice, not a dependency choice.

---

## 9. Visual QA strategy

**Decision:** Hybrid, layered approach — structural/geometric checks
first (page count, dimensions, span bboxes, font names, image counts —
cheap and deterministic), SSIM + raw pixel diff reserved for protected
regions (logos/photos/backgrounds where near-zero diff is expected),
OCR-based comparison (pytesseract) as a bridge check specifically for
catching cases where PDF text objects look structurally fine but
render as garbled/missing glyphs.

**Evidence:** `visual-qa.md`. Confirmed via scikit-image's own API
docs that SSIM measures structural similarity (tolerant of
anti-aliasing noise) rather than raw pixel difference — appropriate
for protected-region checks per master plan Section 37, not for
text-region checks where difference is expected. The OCR-based check
is directly motivated by Decision 7's shaping finding: a page could
pass every structural/geometric check while still containing
mis-shaped Indic glyphs, which only an OCR round-trip (or a human) would
catch.

**Alternatives:** Perceptual hashing (too coarse for this project's
precision needs — not selected as a primary method, could supplement
later), pure pixel diff alone (rejected — master plan Section 37
itself already warns against treating every pixel difference as an
error).

**Why selected:** No single method catches every failure mode this
project cares about (Section 36-37's stated checklist) — layering
addresses that directly, each layer targeting the failure modes the
others miss.

**Why alternatives rejected:** Not fully rejected — perceptual hashing
could be added later as a cheap first-pass filter before the more
expensive SSIM/OCR checks, if performance becomes a concern.

**Risks:** pytesseract requires a separate Tesseract OCR install
(system dependency, not pure-pip) — a new dependency surface to
account for in `dependencies.md` when Phase 9 is reached.

**Future replacement path:** None anticipated at this scope.

---

## 10. Model/runtime strategy

**Decision:** CTranslate2 as the primary path to a usable local
inference runtime for IndicTrans2 (officially documented by AI4Bharat
itself as supported), with the distilled 200M/320M IndicTrans2 models
preferred over the 1B base models for CPU feasibility — but this must
be benchmarked on real target hardware, not assumed from research
alone (see `EXPERIMENTS.md`). Ollama is the runtime for Qwen3
(contextual reasoning role only).

**Evidence:** `indictrans2.md`. No official AI4Bharat CPU/RAM
benchmark exists; a secondary source describes the 1B models as
slow/GPU-hungry, distilled models roughly halving decode time in one
informal test. This is treated as a plausible-but-unverified signal,
not a settled fact.

**Alternatives:** Plain HuggingFace `transformers` inference (simpler
integration, worse CPU performance per available signals), fairseq
inference path (avoids the Windows-incompatible IndicTransToolkit
dependency, but is the less-documented/less-common path per
`indictrans-toolkit.md`).

**Why selected:** CTranslate2 is the only officially-documented
(not just community) path AI4Bharat itself points to for efficient
inference.

**Why alternatives rejected:** Not fully rejected — fairseq remains a
fallback if the Windows/IndicTransToolkit risk (Decision 5) can't be
resolved via WSL2/Docker.

**Risks:** Unverified on this project's actual target hardware.

**Future replacement path:** Re-benchmark if/when GPU hardware becomes
available to the user — GPU path is officially supported and likely
removes the CPU-feasibility question entirely.

---

## 11. Local-only architecture

**Decision:** Unchanged — local-first by default (master plan Section
34, CLAUDE.md privacy rule), external providers opt-in only.

**Evidence:** No research area surfaced a reason to change this. It's
a privacy/product decision, not a technical one open to research
falsification, though CTranslate2 and Qwen3-via-Ollama (Decisions 6,
10) both concretely support local execution being *feasible*, which
de-risks committing to it as the default.

**Alternatives:** N/A (product decision).

**Why selected:** Explicit user/project requirement.

**Why alternatives rejected:** N/A.

**Risks:** CPU-only performance is unverified (Decision 10) — if local
inference proves too slow on real family hardware, the "local-only"
default may need a documented performance caveat, not an architecture
change.

**Future replacement path:** N/A — this is a standing constraint, not
a component to be replaced.

---

## 12. Dependency strategy

**Decision:** Unchanged in principle (master plan Section 63: stage
dependencies, don't front-load) — but the staged list itself is now
sharper. See `docs/dependencies.md` for the concrete CURRENT / NEXT
MILESTONE / FUTURE / OPTIONAL breakdown produced from this research.

**Evidence:** All research areas.

**Why selected:** Confirmed sound; research added specificity
(exact package/repo names, Windows-compat flags, license notes) rather
than changing the staging principle itself.

---

## Summary of changes to `PROJECT_STATE.md`

1. **Translation provider decision** now carries two concrete
   blockers to resolve before implementation: IndicTransToolkit's
   Windows incompatibility, and non-uniform per-language quality
   (Hindi > Telugu/Tamil/Kannada).
2. **OCR backend decision** now carries a known gap: no engine checked
   covers Malayalam; Kannada needs EasyOCR specifically (PaddleOCR
   doesn't cover it).
3. **New, foundational finding**: Indic-script rendering requires
   `insert_htmlbox`, not the classic PyMuPDF text-insertion APIs. This
   must be validated empirically in Milestone 2, not deferred.
4. Both changes are reflected in the updated `PROJECT_STATE.md`.
