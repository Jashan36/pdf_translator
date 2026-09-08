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

## 13. Text-fit measurement strategy (Milestone 3)

**Decision:** Measure fit by actually calling `insert_htmlbox` on a
throwaway, never-persisted `pymupdf.Document` (`core/layout/measurer.py`'s
`TextMeasurer`) rather than building an analytical width/height
formula. The fit algorithm itself (`core/layout/engine.py`'s
`TextFitEngine`) is a deterministic decision tree — original geometry
→ controlled geometry tolerance → binary-search font reduction → structured
failure — built entirely on top of that measurement primitive.

**Evidence:** Decision 7/8's own findings rule out an analytical
shortcut: `Font.text_length()` (naive glyph-advance width) does not
reliably predict `insert_htmlbox`'s actual HarfBuzz-shaped layout for
Indic text, and `insert_htmlbox`'s line-box model is measurably
different from PyMuPDF's own extracted-bbox tightness (confirmed twice
now — once in the rendering proof, again while building Milestone 2's
redact/reinsert proof, which needed `scale_low=0.3` to succeed at all).
Building a parallel measurement formula would risk silently diverging
from the one rendering path this project actually uses.

**Alternatives:** An analytical formula using font metrics
(`Font.text_length`, ascender/descender ratios) — rejected precisely
because it's the thing already shown to diverge from real
`insert_htmlbox` output for Indic text.

**Why selected:** Measurement and the real render path can never
disagree, because they're the same call. The cost is one extra
`insert_htmlbox` invocation per attempted font size (bounded to at
most ~20 by the engine's fixed iteration cap) — negligible for a
single block, not yet benchmarked for whole-document throughput (see
`docs/research/EXPERIMENTS.md`).

**Why alternatives rejected:** An analytical model would need its own
validation against `insert_htmlbox` anyway to be trustworthy, at which
point it's strictly more work than just using `insert_htmlbox` as the
measurement oracle directly.

**Risks:** (a) The binary search assumes standard text-fit
monotonicity — a font size that fits also fits at any smaller size.
True in the general case (less text-width/height is needed as font
size shrinks) but not proven exhaustively across every script/wrapping
edge case in this pass; a pathological case where shrinking changes
word-wrap points in a way that *increases* required height has not
been ruled out. (b) The geometry-expansion "abandon entirely if it
would touch any known obstacle" policy is deliberately conservative —
it will decline expansions a smarter packer could actually make work
(e.g. expanding only on the side away from the obstacle). Both are
tracked in `docs/research/EXPERIMENTS.md`, not silently assumed solved.

**Future replacement path:** If per-block measurement cost becomes a
real bottleneck at whole-document scale (Milestone 4+), consider
caching measurements for identical (text, font, size, width) tuples,
or a validated analytical pre-filter that only calls `insert_htmlbox`
near the actual fit boundary — but only after profiling shows it's
needed, not preemptively.

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

---

## 14. Whole-document pipeline architecture (Milestone 4)

**Decision:** `EXTRACT -> PLAN -> FIT -> VALIDATE PLAN -> MUTATE -> VERIFY`,
implemented as five separate modules under `core/pipeline/`
(`planner.py`, `validator.py`, `executor.py`, `verifier.py`,
`pipeline.py` as the orchestrator) — never
`EXTRACT -> EDIT -> RE-EXTRACT -> EDIT -> ...`. The (immutable)
Document Model is the single source of truth for every stage; nothing
re-derives span/block identity from a post-edit PDF re-extraction.

**Evidence:** Directly required by Milestone 2's finding (this
document, Decision "block identity" note in `PROJECT_STATE.md`'s known
limitations): PyMuPDF's own block `number` field is a positional,
snapshot-local index that shifts after any edit. A pipeline that
interleaved extract/edit/re-extract would silently mismatch blocks
after the first edit. Keying everything by `SourceSpan.span_id`
(stable for the life of one `Document` object) and computing the
entire `TranslationPlan` before any mutation sidesteps this entirely.

**Stable-ID strategy:** `TranslationPlanner._index_spans()` builds a
`span_id -> (SourceSpan, page_index)` map from the Document Model
ONCE, before planning. All downstream stages (validator, executor,
verifier) operate on that plan's own `PlannedTranslation.source_rect`
(captured at planning time), never a fresh lookup. The one place a
fresh re-extraction happens is `DocumentVerifier`, and only to compare
the OUTPUT file against the (already-known) source Document Model
after mutation — that re-extraction is a verification READ, not a
input to any further edit, so it doesn't reintroduce the instability
problem.

**Mutation ordering:** exactly point 5's recommended order — load a
fresh PDF handle, pre-verify every planned region (page index in
range, geometry sane, expected source text present; ANY failure aborts
with ZERO redactions applied), redact all planned regions, commit all
redactions per affected page in one `apply_redactions` call each,
reinsert all translated content via the existing `LayoutRenderer`,
save to a `.tmp` path. The original source file is opened read-only in
effect (a fresh `pymupdf.open()` per pipeline run) and never
overwritten.

**Transaction model:** `TranslationPipeline.run()` only promotes the
`.tmp` output to the real `output_path` (via `os.replace`, atomic on
the same filesystem) after `DocumentVerifier` passes. Any failure at
any stage — fit, validation, mutation, or verification — returns a
structured `PipelineResult` with `output_path=None` and deletes any
temp file already written. This is the point-8 "PASS -> final.pdf /
FAIL -> discard temp" model, implemented literally, not just
conceptually.

**Collision policy:** a second, independent safety layer on top of
Milestone 3's own fit-time obstacle avoidance (`TextFitEngine`'s
`_expand_rect`, which already refuses to expand into a KNOWN
obstacle). The validator (`core/pipeline/validator.py`) re-checks the
COMPLETE set of fitted rects against each other and against every
untouched source object, catching a class of collision the fit engine
alone cannot see: two translated blocks planned independently can each
legitimately avoid the OTHER's original position while still ending up
overlapping each other's final fitted rect (fit-time obstacle checks
only see original geometry, not sibling plans-in-progress). Per point
4's explicit distinction, only NEWLY introduced overlaps are flagged —
a source block already legitimately overlapping something is left
alone (`rect.intersects(other) and not source_rect.intersects(other)`
in every check).

**Verification strategy and `get_text()` limitations:** four
mechanisms, explicitly tagged per check (`VerificationCheck.category`)
so none are conflated (point 9E): structural (opens, page count,
dimensions, mutation count, preserved untouched content/images/
drawings), text-layer (ONLY used to confirm ABSENCE of the original
source string post-redaction — reliable, since it doesn't depend on
`insert_htmlbox`'s corrupted ToUnicode output; never used to confirm
the NEW translated text is byte-correct), pixel (protected regions
must be pixel-identical before/after; translated regions are checked
only for "something changed," not correctness), and OCR (deferred per
point 9D — represented as a `skipped` check via a clean `OCRVerifier`
protocol, not silently omitted or faked).

**Real bug found and fixed during implementation:** the executor's
render-time CSS initially omitted `line-height`/`text-align`, which
`TextMeasurer` (Milestone 3) always includes. This caused
`insert_htmlbox` to lay out text differently at mutation time than it
did during fitting — a plan that measured as `FIT_AFTER_BOTH` then
reported "clipped" when actually rendered. Fixed by carrying
`line_height`/`alignment` through `PlannedTranslation` from
`RenderConfig` at planning time, so the executor's render CSS is
byte-identical to what was measured. This is recorded as a concrete
lesson, not hidden: **any config that affects `insert_htmlbox`
layout must be part of the plan, not re-derived at mutation time** —
a divergence there silently invalidates the fit decision.

**Alternatives:** interleaved extract/edit/re-extract (rejected —
directly contradicted by Milestone 2's own finding); a single
monolithic module instead of 5 separate ones (rejected — point 14
explicitly asks for separated responsibilities, and the separation
paid off immediately by making the CSS bug isolable to one module).

**Risks:** whole-document performance measured on a 5-block, 1-page
fixture (656ms total, ~131ms/block including planning+fit+mutation+
verification) — not yet tested at real multi-page/many-block scale;
verification cost (re-opening 2-3 PDF handles, re-extracting the
output, per-region pixmap renders) is currently the single largest
per-run cost after planning+fit and could dominate at scale. Tracked
in `docs/research/EXPERIMENTS.md`.

**Future replacement path:** if verification cost becomes a bottleneck,
consider narrowing pixel checks to changed regions only (already the
case) plus a sampling strategy for very many untouched blocks rather
than checking every single one — but only once profiling on a real
multi-page document shows it's needed.

---

## 15. Translation engine integration (Milestone 5)

**Decision:** `Document Model -> Translation Units -> TranslationBackend
-> TranslatedSpan/TranslationResult -> quality gates -> Milestone 3
TextFitEngine -> Milestone 4 TranslationPipeline -> PDF` — a backend-
independent `core/translation/` layer sits entirely BEFORE Milestone
4's existing pipeline, connected only through a thin bridge
(`pipeline_bridge.py`) that turns successful `TranslationResult`s into
ordinary Milestone-4 `TranslationInput`s. Milestone 4 itself is
untouched — no PDF architecture redesign, per this milestone's
explicit instruction.

**Evidence:** Confirmed by `test_translation_pdf_e2e.py`'s
`test_full_translation_architecture_uses_no_pymupdf_mutation_apis_directly`,
which parses every file under `core/translation/` and asserts none of
them call `insert_htmlbox`/`add_redact_annot`/`apply_redactions`/
`insert_text`/`insert_textbox` — a structural guarantee, not just a
design intention, that translation code cannot reach into PDF
mutation.

**Backend abstraction:** `TranslationBackend` (a `Protocol`, point 3)
with `translate`/`translate_batch`/`supported_languages`/
`backend_info`. Two implementations exist: `MockTranslationBackend`
(deterministic, zero model dependencies, used by every pipeline/
service test) and `IndicTrans2Backend` (isolated, lazy-imports its
dependencies, raises `TranslationBackendUnavailableError` — never a
bare `ImportError` — when unavailable). Both satisfy the same
interface; nothing outside `indictrans2_backend.py` imports torch/
transformers/IndicTransToolkit, confirmed by
`test_module_imports_unconditionally` passing on a machine with none
of them installed.

**Translation-unit policy (point 5):** one unit per TEXT block
(`core/translation/units.py`), carrying every member span's id, not
just one — the explicit "Total"/"₹"/"1500" non-fragmentation example
is satisfied by construction (`test_multi_span_line_becomes_one_unit_not_three`).
Deliberately NOT sentence-level or semantic grouping, matching the
"deterministic, testable initial policy" instruction. **Known gap,
stated plainly:** `pipeline_bridge.py` maps a multi-span unit's
translated text onto only its FIRST member span's bbox for actual PDF
mutation, because Milestone 4's `TranslationInput` is fundamentally
one-span-per-region — extending that would be a Milestone 4 redesign,
explicitly out of scope here. No current fixture exercises a
multi-span block, so this gap has not yet caused an observed defect,
but it is a real limitation for future content with mixed-style runs
within one line.

**Protected entities (point 6):** regex-based, deterministic
(`core/translation/protected_entities.py`) — URL, email, currency,
date, number, in that priority order (broader/more specific patterns
protected before the generic number pattern would otherwise consume
part of them). Explicitly NOT a full NER/localization system — a
stated v1 scope boundary, not a hidden gap. Protect-then-restore is
verified round-trip-exact when untouched, and `restore()` reports
`all_present=False` (not a silent pass) when a backend drops a
placeholder token — wired into the service's quality gates as
`PLACEHOLDER_MISMATCH`.

**Long-input policy (point 11):** `UnitSplitter`
(`core/translation/splitting.py`) never truncates — either produces
ordered segments (sentence-boundary regex including Devanagari/Indic
`।`) that reassemble to the full input, or returns `None`, which the
service converts to a structured `UNIT_SPLIT_FAILED`, never a
silent content loss. The character-count threshold is an explicitly
documented APPROXIMATION of a real token limit (character-to-subword-
token ratio varies by script/tokenizer) — `IndicTrans2Backend`'s own
`GENERATION_MAX_LENGTH = 256` (confirmed via WebFetch against the
official example code) is the real limit for that specific backend;
wiring the splitter to that exact value per-backend is a follow-up,
not done in this milestone (the default 800-character threshold is a
conservative stand-in).

**Batching (point 10):** `TranslationService.translate_units()` sends
every segment of every unit in ONE `translate_batch()` call
(`test_batching_sends_all_segments_in_one_backend_call` confirms exactly
one call regardless of unit count), and always returns results in the
same order as the input units list — guaranteed by construction (a
single `for unit in units:` loop appending exactly one result per
iteration), not by a separate reordering step that could itself have a
bug.

**Quality gates (point 13):** non-empty output, placeholder
preservation, no stray control characters — checked in
`TranslationService._apply_quality_gates`. Explicitly NOT semantic
quality scoring (out of scope, point 21 forbids it this milestone).

**Determinism (point 14):** `MockTranslationBackend` is fully
deterministic by construction (a lookup table). `IndicTrans2Backend`'s
official generation call sets no sampling parameters (`num_beams=5`,
no temperature/top-k/top-p) — beam search decoding is deterministic
given fixed weights and eval-mode dropout disabled, per direct
inspection of the official `example.py`. This is stated as "should be
deterministic based on the documented API," NOT verified by an actual
repeated-run comparison, since no live run was possible this
milestone (see the feasibility gate below) — the distinction is
recorded honestly rather than claimed as confirmed.

**Feasibility gate result** (`docs/research/indictrans2-feasibility.md`):
native Windows unsupported (official IndicTransToolkit statement,
not attempted); WSL Ubuntu present with adequate hardware (8 cores,
7.6 GiB RAM, 950 GB disk) but this session could not provision `pip`/
`python3-venv` non-interactively (no passwordless `sudo`) — an
environment-ACCESS blocker, not a package-compatibility finding. The
live translation-quality experiment (point 8, all 5 target language
pairs) was **not run** — the adapter is code-complete and interface-
tested (`test_translation_indictrans2_backend.py`, capability-gated
via `pytest.mark.skipif`) but unexercised against a real model. This
is the one Definition-of-Done item (#10, "language pairs
experimentally exercised where the environment supports it") not
fully met, and is recorded as an open item, not silently marked done.

**Alternatives:** forcing the Windows install anyway (rejected —
directly contradicted by the official platform statement, and the
milestone explicitly forbids this); building a from-scratch tokenizer/
preprocessing pipeline to sidestep `IndicTransToolkit` (rejected — the
milestone explicitly forbids reimplementing the official preprocessing
path); skipping the mock backend and only building the real adapter
(rejected — would have made the entire test suite depend on an
uninstallable dependency on this machine, violating point 20 directly).

**Risks:** live IndicTrans2 behavior — actual translation quality, real
CPU inference latency, real memory footprint — remains entirely
unverified on this project's hardware. The 256-token generation cap
is confirmed from official source but its practical interaction with
this project's ~800-character `UnitSplitter` default has not been
tested end-to-end with the real tokenizer. Model licensing (as
distinct from `IndicTransToolkit`'s MIT package license) was not
independently re-verified in this pass.

**Future replacement path:** once environment access is unblocked (see
the feasibility doc's "what would unblock" section), run
`IndicTrans2Backend` against the benchmark fixture (point 8) with zero
code changes anticipated — the adapter was written and interface-
tested specifically so that installing its three dependencies is the
only remaining step.
