# Experiments Required

Questions the research surfaced that documentation alone cannot
answer. Each should be run empirically before or during the milestone
noted, not assumed.

---

## 1. Does `insert_htmlbox` correctly shape Telugu/Devanagari/Tamil/Kannada text with a Noto font? — DONE (2026-09-08)

**Result: GO.** Full write-up: `docs/research/indic-rendering-proof.md`.
Hindi: PASS. Telugu/Tamil/Kannada: PASS WITH LIMITATIONS (native-digit
codepoints render incorrectly — isolated to a narrow PyMuPDF
glyph-selection bug, not font/shaping/CSS — mitigated by using Western
digits for numerals, no architecture change needed). Core shaping
(conjuncts, reordering, wrapping, mixed-script) confirmed correct in
all four languages.

<details><summary>Original experiment plan (superseded by the result above)</summary>

**Why documentation is insufficient:** PyMuPDF's own maintainers
confirm `insert_htmlbox` is the only shaping-capable API (Decision 7,
`ARCHITECTURE_DECISIONS.md`), but a separate official discussion notes
it "still needs a font with correct OpenType tables for the target
script, or it can still fragment glyphs" — a per-font, per-script claim
that must be checked on the actual fonts this project will embed.

**Experiment:** Render a short known-correct sentence in each target
script (e.g. a phrase with a documented conjunct/vowel-reordering case,
like Hindi "क्षत्रिय" or Telugu "క్రొత్త") into a test PDF via
`insert_htmlbox` using the official Noto Sans font for that script.

**Input:** One test PDF per script (4-5 total), each containing 2-3
sentences chosen specifically to exercise conjuncts/reordering, not
simple text.

**Expected observation:** Rendered glyphs visually match the correct
shaped form when the PDF is opened in a standard viewer (and ideally
cross-checked via OCR round-trip per Decision 9).

**Metric:** Pass/fail per script — does the rendered text look correct
to a native/fluent reader, and does OCR (pytesseract, correct language
pack) recover the original string?

**Decision threshold:** Any script that fails must have its Noto
font/config investigated before Milestone 2 is considered complete for
that language — do not silently ship broken rendering for one script
while others work.

**Milestone:** 2 (Exact Text Replacement) — this should be the first
thing proven, per Decision 7's "action required" note.

</details>

---

## 1b. Follow-up (optional, not blocking): does a static (non-variable) Noto font fix the native-digit bug?

Raised by Experiment 1's isolation work. Not required to proceed
(Western-digit mitigation already unblocks Milestone 2), but worth
tracking if native-script digit output is ever explicitly requested.

**Why documentation is insufficient:** The isolation in
`docs/research/indic-rendering-proof.md` ruled out font glyph
coverage, shaping, HTML/CSS, and general script handling — but did not
test whether the bug is specific to *variable* fonts (all four fonts
tested were variable TTFs) versus a static instance of the same
design.

**Experiment:** Render the same native-digit strings using a static
(single-weight, non-variable) build of Noto Sans Tamil/Telugu/Kannada
instead of the variable TTF.

**Input:** A static instance of each font (e.g. instantiated via
fontTools, or a pre-built static release if the notofonts project
publishes one) + the same digit test strings from Experiment 1.

**Expected observation:** Either the bug disappears (confirming a
variable-font-specific PyMuPDF parsing issue) or persists (narrowing
further to something else about these specific fonts/codepoints).

**Metric:** Pass/fail per script.

**Decision threshold:** Only relevant if a user explicitly needs
native-script digit rendering; otherwise the Western-digit mitigation
stands indefinitely.

**Milestone:** None scheduled — track as a backlog item.

---

## 1c. Can `insert_htmlbox`'s text-layer (ToUnicode) corruption be fixed or worked around?

Discovered during Milestone 2 implementation (see
`ARCHITECTURE_DECISIONS.md` Decision 7's Milestone-2 update), not part
of the original rendering proof, which only checked visual output.

**Why documentation is insufficient:** `insert_htmlbox`'s official
docs describe its rendering/layout behavior but not the correctness of
the ToUnicode CMap it generates for the embedded font subset.

**Experiment:** Insert the same Indic string via `insert_htmlbox` and
via `insert_text`+`fontfile=`, save both, reopen, call
`page.get_text("text")` on each, and diff against the known-correct
input string. (Already done once, informally, during Milestone 2 —
this entry is to formalize a broader per-script/per-length check and
to investigate whether a documented flag or post-processing step
(e.g. manually setting `/ToUnicode` on the generated font's xref, or a
future PyMuPDF option) can fix `insert_htmlbox`'s output rather than
just working around it.

**Input:** A range of Indic strings per script (short/long,
conjunct-heavy/simple), inserted via both APIs.

**Expected observation:** Consistent corruption via `insert_htmlbox`
(already observed once) vs. correct round-trip via `insert_text`.

**Metric:** Percentage of characters/strings that round-trip correctly
per API per script.

**Decision threshold:** If no fix is found, document this as a
permanent, accepted limitation of the translated-PDF output (searchable
text will not always match displayed text for Indic scripts) and rely
exclusively on rendered-pixel/OCR-based QA (Decision 9) rather than
text-layer QA for these scripts — do not silently ship this without
disclosing it as a known limitation (master plan Section 58's
"controlled fidelity, not impossible universality" principle).

**Milestone:** Before Milestone 9 (Visual QA) is considered complete,
since it determines whether text-layer QA can be trusted at all for
Indic-script content.

## 2. Does `Font.text_length()` accurately predict `insert_htmlbox`'s actual shaped width for Indic text?

**Why documentation is insufficient:** `Font.text_length()` measures
naive glyph-advance width; `insert_htmlbox` shapes via HarfBuzz, which
can produce different effective widths for conjuncts/ligatures. No
source directly confirmed or denied whether these two numbers agree
for Indic scripts.

**Experiment:** For a range of Telugu/Hindi/Tamil/Kannada strings of
varying length, compute `Font.text_length()` and separately measure
the actual rendered width of an `insert_htmlbox`-rendered box
(e.g. via the returned layout info or by rendering and measuring pixel
bounds).

**Input:** ~20 strings per script, mixing short/long and
conjunct-heavy/simple text.

**Expected observation:** A consistent ratio or an inconsistent,
script/content-dependent discrepancy.

**Metric:** Percent difference between predicted and actual width, per
script.

**Decision threshold:** If discrepancy exceeds ~10-15% for any script,
the layout-fit binary search (Decision 8) must use a corrected
estimate or fall back to iterative `insert_htmlbox` measurement instead
of trusting `Font.text_length()` alone.

**Milestone:** 3 (Automatic Text-Fit Engine).

---

## 3. How much longer is Telugu/Hindi/Tamil/Kannada output than English, in practice?

**Why documentation is insufficient:** No source quantifies expected
text-expansion ratios for these specific language pairs in a PDF
localization context (general "translation expands text" knowledge
exists but isn't a verified, language-specific number for this
project's actual content style).

**Experiment:** Translate a representative sample from the master
plan's test corpus (Section 54, Test PDFs A-E) into each target
language via the chosen translation path, and measure character/pixel-width
ratio vs. the English source, per block type (heading, paragraph,
table cell, caption).

**Input:** Test PDFs A-E (once they exist) translated into all 4
languages.

**Expected observation:** A distribution of expansion ratios, likely
different per language and per block type.

**Metric:** Median and 90th-percentile expansion ratio per
language/block-type combination.

**Decision threshold:** Feeds directly into calibrating the text-fit
engine's font-size-reduction tolerance (master plan Section 19's
"minimum 15pt" example) — if actual expansion regularly exceeds what a
15% font-size reduction can absorb, the tolerance or fallback strategy
needs revisiting before Milestone 3 is considered tuned.

**Milestone:** 3-4.

---

## 4. How often does translation overflow the original bounding box, and does the wrap/shrink fallback chain actually resolve it?

**Why documentation is insufficient:** This is an emergent property of
the whole pipeline (extraction accuracy + translation length +
shaping + fit algorithm), not something any single library's docs can
answer.

**Experiment:** Run the full Milestone 3 pipeline against the test
corpus and record, per text block: did it fit at original size? at
reduced size? did it need wrapping? did it end in LAYOUT_WARNING?

**Input:** Test PDFs A-J (master plan Section 54) once available.

**Expected observation:** A distribution across
fit/shrink/wrap/warning outcomes.

**Metric:** Percentage of blocks in each outcome category, per
language.

**Decision threshold:** If LAYOUT_WARNING rate is high (no fixed
number yet — establish a baseline first run, then track regression),
investigate whether the fit algorithm's tolerances (Decision 8) need
adjustment before calling Milestone 3 complete.

**Milestone:** 3, revisited at 9 (Visual QA) once the full corpus
exists.

---

## 5. Which translation granularity (paragraph vs. section-context-window) gives better contextual accuracy for this project's actual documents?

**Why documentation is insufficient:** `translation-architecture.md`'s
recommendation (paragraph-level with a bounded sliding-context window)
is based on general document-MT literature and Google's documented
approach, not on evidence from this project's own document types
(nutrition guides, brochures, etc. per the master plan's examples).

**Experiment:** Translate the same test document twice — once with
paragraph-only context, once with the full layered context package
(document summary + section summary + sliding window) — and compare
using the `translation-quality` skill's checklist (pronoun resolution,
terminology consistency, protected-term survival).

**Input:** A test document with cross-paragraph pronoun references and
repeated terminology (e.g. the master plan's own "iron... it... iron"
example, Section 6).

**Expected observation:** The full-context version resolves references
and maintains terminology better than paragraph-only, per the
translation-quality checklist.

**Metric:** Count of terminology-consistency failures and
pronoun-resolution failures per approach.

**Decision threshold:** If full context shows no measurable
improvement over paragraph-only for this project's actual content, the
simpler paragraph-only approach should be preferred (per CLAUDE.md's
"minimal change" development-protocol rule) — don't carry the extra
context-building complexity without evidence it helps.

**Milestone:** 5-6.

---

## 6. Can IndicTransToolkit run reliably enough via WSL2/Docker on the target Windows machine, or does it block the IndicTrans2 path entirely?

**Why documentation is insufficient:** The toolkit's own README states
it's not built/tested for Windows, but doesn't say whether a
WSL2/Docker workaround is reliable in practice for this specific use
case (a local Streamlit app that needs to call into it).

**Experiment:** Attempt an install and a minimal translation call
inside WSL2 (or Docker) on the actual development machine, calling it
either via a subprocess/IPC bridge from the Windows-hosted Streamlit
app or by running the whole app inside WSL2.

**Input:** A minimal IndicTrans2 + IndicTransToolkit "translate one
sentence" script.

**Expected observation:** Either a working call path with acceptable
latency, or a concrete blocking error.

**Metric:** Success/failure, and latency if successful.

**Decision threshold:** If no reliable Windows-compatible path
(WSL2/Docker or otherwise) is found, fall back to Google Cloud
Translation or Argos for the default path (Decision 5's fallback), and
treat IndicTrans2 as an optional/advanced path documented as
Linux/WSL2-only.

**Milestone:** 5, before committing IndicTrans2 as anything more than
an optional path.

---

## 7. Does PaddleOCR/EasyOCR/docTR actually support Malayalam, contrary to what this research pass found?

**Why documentation is insufficient:** This research checked official
sources for all three engines and found no confirmed Malayalam
recognition support — but this is a negative finding (absence of
evidence), which is weaker than a positive confirmation and worth a
direct check against each engine's current language-list documentation
or a minimal test run, since OCR language-support lists change
between releases.

**Experiment:** Check each engine's current officially-documented
supported-language list directly (not via this research's secondary
summary) at the time Phase 7 begins, and/or run a minimal OCR test on
a small Malayalam text image.

**Input:** A Malayalam text sample image.

**Expected observation:** Either confirmed non-support (matching this
research) or a newer release that added it.

**Metric:** Pass/fail per engine.

**Decision threshold:** If still unsupported everywhere, Malayalam
scanned-PDF support should be explicitly scoped out of Phase 7 and
documented as a known gap, not silently attempted with a
poorly-performing engine.

**Milestone:** 7 (OCR), only if Malayalam support is actually required
by the user at that point.

---

## 8. Does the text-fit binary search's monotonicity assumption ever break?

Raised by Decision 13 (Milestone 3). The engine's binary search assumes
"a font size that fits also fits at any smaller size" — true in the
general case, not proven exhaustively.

**Why documentation is insufficient:** This is an assumption about
`insert_htmlbox`'s own wrapping/layout behavior across arbitrary text,
which no PyMuPDF documentation makes a formal guarantee about either
way.

**Experiment:** Across a large sample of real translated text
(once translation exists, Milestone 5+) and the fixture cases in
`tests/fixtures/fit_cases.py`, run the fit engine at every font size in
a fine-grained sweep (not just the binary-search path) and check for
any case where a smaller size required MORE height than a larger one
(would indicate a wrapping-induced monotonicity violation).

**Input:** The existing fit-case fixtures plus real translated content
once available.

**Expected observation:** No violations (supporting the current
assumption) or a specific, reproducible counter-example.

**Metric:** Count of monotonicity violations found, if any.

**Decision threshold:** If a violation is found, the engine's binary
search needs a monotonicity-safe fallback (e.g. verify the final
chosen size directly rather than trusting the search path, which the
engine already does as a safety net — see `engine.py`'s
"re-confirm after snapping" step — but a systematic violation would
mean the search could miss a better-fitting larger size, not just
report a wrong one).

**Milestone:** Before Milestone 4 (whole-document application of this
engine) treats the assumption as safe at scale.

---

## 9. Is the "abandon expansion entirely on any obstacle contact" geometry policy too conservative?

Raised by Decision 13 (Milestone 3). The current policy declines an
expansion completely if the grown rect would touch ANY known obstacle,
even if a smaller/differently-shaped expansion (e.g. only rightward,
not downward) would avoid it.

**Why documentation is insufficient:** This is a project-specific
policy choice, not a library behavior to verify against docs.

**Experiment:** On real multi-block pages (the golden fixture, and
real translated documents once available), measure how often
expansion is abandoned due to an obstacle vs. how often a smarter
directional/partial expansion could have succeeded instead.

**Input:** Pages with tightly-packed blocks/images near translated
text blocks.

**Expected observation:** A rate of "unnecessarily abandoned"
expansions.

**Metric:** Percentage of NO_FIT/FIT_AFTER_FONT_REDUCTION outcomes
that could have instead been FIT_AFTER_GEOMETRY_TOLERANCE with a
smarter policy.

**Decision threshold:** If this rate is high enough to noticeably hurt
output quality, implement directional expansion (grow only away from
the nearest obstacle) as a Milestone 4+ refinement — not now, since
the current conservative policy is safe (never damages a document) and
untested-but-plausible is not sufficient justification to add
complexity yet (CLAUDE.md's "minimal change" development-protocol rule).

**Milestone:** 4 (whole-document redact/reinsert pipeline), if profiling
against real documents shows this matters.

---

## 10. What is the per-block measurement cost of the fit engine at whole-document scale?

Raised by Decision 13. Each `TextFitEngine.fit()` call opens/closes at
least 2, up to ~20+2, throwaway `pymupdf.Document` instances (one per
attempted font size, plus the diagnostic height probe on failure).

**Why documentation is insufficient:** This is a performance question
about this project's own usage pattern, not something PyMuPDF's docs
address.

**Experiment:** Run the fit engine across every text block in a
representative multi-page document (e.g. the golden fixture repeated
across many pages, or a real translated document once available) and
measure wall-clock time per block and per document.

**Input:** A multi-page, many-block document.

**Expected observation:** A total time budget acceptable for a local
Streamlit app's interactive use (per master plan Section 33's
"family/local, not enterprise-scale" framing).

**Metric:** Milliseconds per block, total seconds per document.

**Decision threshold:** If unacceptably slow, consider the caching or
analytical-prefilter options noted in Decision 13's "future
replacement path" — but only once profiling shows an actual need.

**Milestone:** 4, before whole-document application at scale.

**Partial result (2026-09-08, this session):** Ran the 15
`tests/fixtures/fit_cases.py` cases (a realistic mix of fit-on-first-try
and worst-case-8-attempts blocks) through the real `TextFitEngine`.
Total: 339ms for 15 blocks, average 22.6ms/block (range: ~6.5ms for a
single-attempt fit, ~43ms for an 8-attempt binary-search case). This
is real measured data, not an estimate — a 50-block document would be
on the order of ~1 second of fit-engine work, well within acceptable
range for a local Streamlit app per master plan Section 33's framing.
Not yet tested: a genuinely large multi-page document (hundreds of
blocks), or whether repeated `pymupdf.open()`/`close()` calls (one per
measurement) show any cumulative slowdown over thousands of calls in
one process — that remains open for Milestone 4.

**Update (Milestone 4, 2026-09-08):** Ran the full whole-document
pipeline (`TranslationPipeline.run()`) across 5 blocks (Telugu, Hindi,
Tamil, Kannada, mixed) on the Milestone 4 fixture. Real measured
totals: 656.6ms end-to-end (131.3ms/block average), broken down as
planning+fit 365.0ms (73ms/block — higher than Milestone 3's isolated
22.6ms/block, since these particular translations needed font-
reduction/expansion searches), validation 0.5ms (negligible — a pure
in-memory geometry pass), mutation 142.8ms (redaction + reinsertion +
save for 5 blocks), verification 148.2ms (opens 2-3 PDF handles,
re-extracts the output document, per-region pixmap renders). For 1
page / 5 blocks this is well within interactive range for a local app;
whole-document scale (many pages, dozens+ of blocks) is untested —
see Experiment 11 below.

---

## 11. Whole-document pipeline performance at real multi-page scale

Raised by Decision 14 (Milestone 4). Only tested at 1 page / 5 blocks
so far (Experiment 10's update).

**Why documentation is insufficient:** this is entirely this project's
own usage pattern; no library documents it.

**Experiment:** Run `TranslationPipeline.run()` against a synthetic or
real multi-page document (tens of pages, dozens to hundreds of
translatable blocks) and record the same per-stage timings (planning+
fit, validation, mutation, verification, total).

**Input:** A large multi-page fixture (could extend
`tests/fixtures/pipeline_multilingual.pdf`'s generator to repeat its
page N times) with translations supplied for every block.

**Expected observation:** Roughly linear scaling of planning+fit and
mutation with block count (each block's `insert_htmlbox` measurement/
render calls are independent); verification cost may scale worse,
since it currently re-extracts the FULL output document and iterates
every untouched span/image/drawing on every page even when only a few
blocks changed.

**Metric:** ms/block and ms/page at increasing document sizes; whether
verification's share of total time grows disproportionately.

**Decision threshold:** If verification dominates at scale, consider
narrowing its structural "preserved content" pass to only the pages
that were actually touched (skip full re-extraction of untouched
pages entirely) — a targeted optimization, not a redesign, and only
once this experiment shows it's actually needed (CLAUDE.md's minimal-
change rule).

**Milestone:** Before Milestone 4's pipeline is used on real,
non-fixture documents at production scale.

---

## 12. Is the two-layer collision defense (fit-time obstacle avoidance + plan-level validator) sufficient, or does it still miss cases?

Raised by Decision 14. The validator catches collisions the fit
engine's own obstacle avoidance can't see (independently-planned
blocks whose FINAL fitted rects overlap even though neither touched
the other's ORIGINAL position) — but this was only exercised via
synthetic/injected test plans (`test_pipeline_e2e.py`'s stub-planner
tests), not via organic multi-block fitting on a real document where
many blocks are translated at once and genuinely compete for space.

**Why documentation is insufficient:** project-specific emergent
behavior across many simultaneous fit operations, not a library
question.

**Experiment:** Translate EVERY block on a densely-packed real page
(more blocks, less whitespace than the current fixture) with
`allow_geometry_expansion=True` and a realistic (not deliberately
extreme) `max_expansion_ratio`, and check how often the validator
actually catches a genuine emergent collision vs. how often Milestone
3's fit-time obstacle avoidance alone already prevented it.

**Input:** A densely-packed multi-block fixture.

**Expected observation:** A count of validator-caught collisions on
realistic (non-synthetic) input.

**Metric:** Collision rate; whether any collision slips past BOTH
layers (would be a serious finding requiring immediate architecture
attention, not a backlog item).

**Decision threshold:** If collisions are ever found to slip past both
layers, that is a Decision-14-invalidating finding and must update
`ARCHITECTURE_DECISIONS.md` immediately, not be filed as routine
backlog. If the validator simply never fires on realistic input
(because fit-time avoidance already prevents everything), that's
useful confirmation the two-layer design is working as intended, not
evidence the second layer is unnecessary (it remains defense-in-depth
against the fit engine's own scope limits, e.g. Experiment 9's
conservative-expansion policy potentially changing).

**Milestone:** Before Milestone 4's pipeline is trusted on real,
densely-packed documents.
