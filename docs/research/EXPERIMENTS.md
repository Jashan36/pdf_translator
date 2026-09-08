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
