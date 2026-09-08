# Project State

Read this before making any change. Update it after every milestone or
significant decision. This is the working memory that replaces "one
giant prompt" — see CLAUDE.md's development protocol.

## Current milestone

**Milestone 3 — Automatic Text-Fit Engine: DONE (2026-09-08).**

### Completed components

- `core/layout/models.py` — `TextFitRequest` (source id, target text,
  language/script, available rect + `safety_inset`, style, font
  family/file, initial/min font size, line-height/alignment policy,
  overflow tolerance, horizontal-scaling/geometry-expansion flags,
  page bounds, obstacle rects, rendering mode, numeral-fallback flag,
  font-size search step), `TextFitResult` (status, final font
  size/rect, scale, spare height, line-count estimate, overflow,
  attempted font sizes, geometry decision, digit-fallback flag,
  rendered text, reason), `FitStatus` taxonomy (`FIT`,
  `FIT_AFTER_GEOMETRY_TOLERANCE`, `FIT_AFTER_FONT_REDUCTION`,
  `FIT_AFTER_BOTH`, `NO_FIT_MIN_FONT_SIZE`, `INVALID_GEOMETRY`,
  `MISSING_FONT`, `RENDER_ERROR`), `ScriptCategory` (LATIN/INDIC/MIXED/
  OTHER), `GeometryDecision`.
- `core/layout/measurer.py` — `TextMeasurer`: measures fit by actually
  calling `insert_htmlbox` on a throwaway, never-persisted
  `pymupdf.Document` (per Decision 13 — no analytical formula was
  trusted, since Milestone 2 already showed `Font.text_length()`
  diverges from real `insert_htmlbox` layout for Indic text). Also
  provides `measure_required_height()`, a diagnostic-only probe used
  for overflow/line-count reporting on failure, never for the pass/fail
  decision itself.
- `core/layout/engine.py` — `TextFitEngine.fit()`: the deterministic
  decision tree (original geometry → controlled geometry tolerance →
  binary-search font reduction, fixed 20-iteration cap → structured
  `NO_FIT_MIN_FONT_SIZE`). Forces `allow_horizontal_scaling=False` for
  `ScriptCategory.INDIC` regardless of the request. Never mutates its
  input request/style. `TextRenderer` in the brief's
  Measurer/Engine/Renderer split is the EXISTING `core/pdf/renderer.py`
  `LayoutRenderer` — reused, not reinvented (see that file's updated
  docstring).
- `core/layout/numerals.py` — `apply_native_digit_fallback()`: the
  Milestone-2 native-Indic-digit rendering bug (Telugu/Tamil/Kannada,
  not Devanagari) modeled explicitly as a renderer-compatibility
  fallback applied ONLY to an internal rendering-time text copy —
  `TextFitRequest.text` (the actual translation) is never touched, and
  `TextFitResult.native_digit_fallback_applied`/`rendered_text` make
  the substitution visible to callers rather than silent.
- `tests/fixtures/fit_cases.py` — the dedicated fit fixture (point J):
  15 structured cases spanning English/Telugu/Hindi/Tamil/Kannada,
  mixed-script, short/long strings, an unbreakable long word,
  punctuation, Western and native-script numbers, tight/roomy/
  deliberately-impossible rects.
- 36 new tests (`test_layout_numerals.py`, `test_layout_measurer.py`,
  `test_layout_engine.py`) covering all 16 cases point I asks for plus
  the `safety_inset` geometry concept — 68 tests passing total.

### Experimentally observed behavior (not claimed, measured)

- Fit-engine cost across the 15 fixture cases: **339ms total, 22.6ms/
  block average** (range ~6.5ms single-attempt fit to ~43ms an
  8-attempt binary search) — see `docs/research/EXPERIMENTS.md` #10.
  Acceptable for a local Streamlit app at the scale tested; whole-document
  scale (hundreds of blocks) not yet tested.
- Binary search converges within its 20-iteration cap on every fixture
  case tested (typically 6-8 attempts to converge from an 18pt→6pt
  range at a 0.5pt step) — never needed the full cap in this pass.

### Remaining components / open questions (explicitly not resolved here)

- **Monotonicity assumption unverified at scale** (`docs/research/EXPERIMENTS.md`
  #8): the binary search assumes a smaller font size always fits if a
  larger one does. True in general, not exhaustively proven across
  every wrapping edge case.
- **Geometry-expansion policy is deliberately conservative**
  (`docs/research/EXPERIMENTS.md` #9): abandons expansion entirely if
  it would touch ANY known obstacle, rather than trying a smarter
  partial/directional expansion. Safe (never damages a document) but
  may decline fits a smarter policy could achieve — left conservative
  on purpose per CLAUDE.md's "minimal change" rule, not because a
  better policy is impossible.
- **Whole-document application not built** — this milestone fits ONE
  block/span per `TextFitEngine.fit()` call; a pipeline that plans
  every block on a page/document, applies all edits, and only then
  re-extracts (per known limitation #2 below) is Milestone 4 territory.
- **No new dependencies were needed** — `pymupdf`/`pydantic` already
  covered everything; `docs/dependencies.md` unchanged this milestone.

**Next: Milestone 4 — whole-document redact/reinsert using the
text-fit engine's plans**, informed by Experiments #8/#9/#10 above and
Milestone 2's known limitation #2 (extract once, plan everything, edit
in one pass, don't interleave extract/edit/re-extract).

---

## Previous milestones

### Milestone 2 — Document Model: DONE (2026-09-08).

#### Completed components

- `core/geometry.py` — `PdfRect`/`PdfQuad`: real `pymupdf.Rect`/`Quad`
  objects held in memory, fully JSON-serializable via pydantic
  `PlainValidator`/`PlainSerializer` (no raw PyMuPDF object ever hits
  JSON). Documents the coordinate convention (PyMuPDF space: origin
  top-left, y down — not raw PDF space).
- `core/models.py` — normalized Document Model: `Document` → `Page` →
  `Block` → `Line` → `SourceSpan`/`TranslatedSpan`, plus `Image`,
  `Drawing`, `Table` (placeholder), `TextStyle`. `SourceSpan` is
  **frozen** (pydantic immutable) — a translation is always a separate
  `TranslatedSpan` linked by `source_span_id`, never a mutation.
- `core/pdf/extractor.py` — `PDFExtractor.extract_document(path) ->
  Document`, the ONE place PyMuPDF extraction logic lives. Captures
  span `origin`/`ascender`/`descender`/`alpha`/`char_flags` (richer
  than Milestone 1), block/line/span nesting mirroring PyMuPDF's own
  `get_text("dict")` shape.
- `core/pdf/analyzer.py` — reduced to a thin wrapper over
  `PDFExtractor` (kept `is_native_text_pdf` for the forensics view) —
  no duplicate extraction logic.
- `core/serialization.py` — `serialize_document`/`deserialize_document`/
  `save_document`/`load_document`; JSON round-trips exactly, verified
  against real extracted data, not just a hand-built minimal example.
- `core/pdf/renderer.py` — `LayoutRenderer.render_translated_block()`,
  the interface a future renderer needs. Uses `insert_htmlbox`
  exclusively (per Decision 7) — never the classic text APIs.
- `core/pdf/redact_reinsert.py` — `redact_and_reinsert_span()`: the
  single-block redact/reinsert proof (`add_redact_annot` +
  `apply_redactions`, scoped tightly to one span's bbox, then
  `insert_htmlbox` reinsertion). Proof passes on real Telugu content in
  `tests/test_redaction_reinsertion.py`, with visual evidence in
  `docs/research/assets/redact-reinsert-proof/`.
- `tests/fixtures/golden_multilingual.pdf` (+ its generator,
  `scripts/fixtures/build_golden_multilingual.py`) — English, Telugu,
  Hindi, Tamil, Kannada, mixed-script, an embedded image, a vector
  drawing, 9 blocks total. Built with `insert_text`+`fontfile=`, NOT
  `insert_htmlbox` — see "known limitations" below for why.
- 32 tests passing across `test_document_model.py`, `test_geometry.py`,
  `test_extraction.py`, `test_serialization.py`,
  `test_rendering_integration.py`, `test_redaction_reinsertion.py`
  (plus the original Milestone 1 tests, still green).
- `app.py` updated to the new nested model shape (blocks/lines/spans
  instead of a flat `text_objects` list).

#### Remaining components (explicitly NOT done — future milestones)

- Whole-document redact/reinsert pipeline (only a single controlled
  block was proven, per instructions — Milestone 3/4 territory).
- Automatic text-fit engine (font-size search, wrapping) — **now DONE,
  see Milestone 3 above** — the redact/reinsert proof needed a
  permissive `scale_low` to succeed at all, which was Milestone 3's
  job to calibrate properly, not Milestone 2's.
- Table extraction (`Table`/`TableCell` are placeholder structures with
  no populated rows/cols yet, as instructed).
- Any translation logic — `TranslatedSpan` exists as a model/interface
  target only; no translation engine is wired up.

#### Known limitations discovered during implementation

1. **`insert_htmlbox` corrupts the PDF's text layer (ToUnicode),
   even though it renders visually correctly.** Discovered while
   building the golden fixture: a Telugu string inserted via
   `insert_htmlbox`, saved, and re-extracted via `get_text()` came back
   with wrong characters (visual rendering was still correct). The
   identical string via `insert_text`+`fontfile=` round-tripped
   byte-exact. This is why the golden fixture uses `insert_text` (for
   byte-exact known ground truth), while `insert_htmlbox` remains the
   only path used for actual rendering (visual correctness, per the
   accepted rendering proof) — a real tradeoff between the two APIs,
   not a strict improvement in either direction. Practical consequence:
   translated PDF output may look right but fail copy-paste/search/
   screen-reader access. See `docs/research/ARCHITECTURE_DECISIONS.md`
   Decision 7's Milestone-2 update and `docs/research/EXPERIMENTS.md`
   #1c. QA (Milestone 9) must rely on rendered-pixel/OCR verification,
   not `get_text()`, for translated content correctness.
2. **Block IDs are positional, not stable across edits.** `block_id`
   is derived from PyMuPDF's own `get_text("dict")` block `number`
   field, which is a snapshot-local index — redacting one block shifts
   every later block's number in a fresh re-extraction. Confirmed while
   writing the redact/reinsert test (matching by `block_id` across a
   before/after edit silently compared the wrong blocks; fixed to match
   by text content instead). Implication for later milestones: a
   whole-document translation pipeline should extract once, plan every
   target rect, and apply all edits before any re-extraction — not
   interleave extract→edit→re-extract→edit cycles that rely on block
   identity surviving an edit.
3. **A translated span's bbox is usually not tall enough for
   `insert_htmlbox`'s own line-box model**, even for identical-length
   text at the same font size — the extracted bbox is tight to glyph
   ink extents, while `insert_htmlbox` computes its own line-height.
   The redact/reinsert proof needed `scale_low=0.3` (permissive
   shrinking) to succeed; Milestone 3's text-fit engine needs to
   calibrate this properly (padding, line-height assumptions) rather
   than relying on shrinkage as the default behavior.

**Rendering proof-of-concept (prerequisite for Milestone 2):
DONE (2026-09-08), result GO** — see `docs/research/indic-rendering-proof.md`
and the "Full technical research pass" section below. Not repeated
here. Milestone 3 (above) directly addressed known limitation #3.

## Full technical research pass: DONE (2026-09-08)

Ran across 5 parallel research agents; all findings in
`docs/research/` — see `docs/research/ARCHITECTURE_DECISIONS.md` for
the 12 synthesized decisions, `docs/research/SOURCES.md` for the
aggregated source list, and `docs/research/EXPERIMENTS.md` for
questions that need empirical validation, not just documentation.

**One finding changes the plan materially, not just refines it:**
PyMuPDF's classic text-insertion APIs (`insert_text`, `insert_textbox`,
`TextWriter`) **cannot** render Indic scripts correctly — confirmed
directly by PyMuPDF's own maintainers. All Indic-script text insertion
must use `page.insert_htmlbox()` (HarfBuzz-backed). Milestone 2 must
validate this empirically (`docs/research/EXPERIMENTS.md` #1) as close
to its first task as possible, not defer it.

## Open decisions (not yet made — do not assume)

- **Translation provider for Milestone 5+**: still undecided, but now
  with two concrete blockers to resolve first (not just "pick one"):
  1. IndicTransToolkit (required for IndicTrans2's practical inference
     path) is community-maintained, not an official AI4Bharat repo,
     and explicitly not built/tested for Windows — this dev
     environment is Windows. Needs `docs/research/EXPERIMENTS.md` #6
     (WSL2/Docker feasibility check) before committing.
  2. Translation quality is not uniform across target languages —
     Hindi (Indo-Aryan) outperforms Telugu/Tamil/Kannada (Dravidian)
     per IndicTrans2's own benchmark paper. Don't present these as
     equal-quality to the user once implemented.
  Candidates remain: IndicTrans2 (primary candidate per CLAUDE.md,
  now evidence-backed), Google Cloud Translation (cloud fallback, no
  Windows-compat risk), Argos Translate (offline fallback), Gemini API
  (contextual mode). Do not pick without running Experiment 6 or
  asking the user.
- **OCR backend**: PaddleOCR (PP-OCRv5/v6) confirmed as primary
  candidate, but with a real gap: it does **not** support Kannada or
  Malayalam recognition. EasyOCR is needed as a secondary path for
  Kannada. No engine checked (PaddleOCR, EasyOCR, docTR) confirms
  Malayalam support — see `docs/research/EXPERIMENTS.md` #7. Not
  needed until Milestone 7.
- **Qwen3 model size**: confirmed role (contextual review/QA, not
  primary translator) but which size (`0.6b`–`235b`) is practical on
  target hardware is unresolved — needs its own experiment when
  Milestone 6 begins.

## Milestone roadmap (master plan Section 53, as tracked in this session)

Note: this session's "Milestone 2" (Document Model) is a superset of
master plan Section 53's M2 groundwork — it built the full normalized
model/extraction/serialization layer plus a single-block redact/
reinsert proof, rather than only "exact text replacement." This
session's "Milestone 3" built the deterministic text-fit engine but
NOT its whole-document application — that remains M4 below.

1. ✅ PDF Forensics (`PDF → inspect → JSON`)
2. ✅ Document Model + single-block redact/reinsert proof (this session)
3. ✅ Automatic text-fit engine (geometry tolerance → binary-search
   font reduction → structured NO_FIT; this session) — whole-document
   application deferred to M4
4. ⬜ Whole-document redact/reinsert pipeline, applying the text-fit
   engine's plans across every block on a page (extract once, plan
   everything, edit in one pass — per Milestone 2's known limitation #2)
4b. ⬜ Language detection
5. ⬜ Translation provider integration
6. ⬜ Context-aware (paragraph-level) translation
7. ⬜ OCR for scanned PDFs
8. ⬜ Tables and complex layout
9. ⬜ Visual + semantic QA
10. ⬜ Family-friendly UI polish

## Repo layout notes

- Git worktrees are in use — changes land in a worktree branch first
  and must be merged into `main` in the real project folder
  (`C:\Users\91918\Desktop\PDF_TRANSLATOR`) before the user can run
  them. Always confirm the merge happened.
- `.claude/skills/` holds custom project skills (see below) —
  discovered automatically by Claude Code at session start.
- `docs/dependencies.md` — running log of verified dependencies,
  staged CURRENT/NEXT MILESTONE/FUTURE/OPTIONAL.
- `docs/research/` — full upfront technical research pass (done
  2026-09-08): per-topic files (pymupdf, pdf-internals, ocr,
  document-parsing, indictrans2, indictrans-toolkit,
  translation-architecture, qwen3-ollama, pdf-typography,
  layout-fitting, visual-qa, streamlit), plus
  `ARCHITECTURE_DECISIONS.md` (13 synthesized decisions, updated as
  implementation surfaces new findings), `SOURCES.md` (aggregated
  citations), and `EXPERIMENTS.md` (10 empirical validations, several
  still open — read before assuming a research finding is final).
  Also `indic-rendering-proof.md` (Milestone 2 rendering
  proof-of-concept) and `assets/` (rendered evidence PNGs/PDFs for
  both the rendering proof and the redact/reinsert proof).
- `core/layout/` — Milestone 3's text-fit engine (`models.py`,
  `measurer.py`, `engine.py`, `numerals.py`). `core/pdf/renderer.py`'s
  `LayoutRenderer` is the "TextRenderer" this connects to, not a
  separate module.

## Custom skills installed

- `pdf-forensics` — inspect PDF internals before modifying.
- `pdf-layout-analysis` — geometry/reading-order/table/layout rules.
- `indic-language-translation` — verified Indic-language facts
  (scripts, codes, IndicTrans2), never guess.
- `translation-quality` — evaluate translations beyond word-swap.
- `visual-pdf-qa` — original-vs-translated render comparison protocol.
- `technical-research` — verification-first research protocol for any
  unfamiliar library/API/model.
- `dependency-verification` — verify before adding any dependency.

## Environment notes

- Python venv at `.venv/` (not committed). `pip install -r
  requirements.txt` to set up.
- Run: `streamlit run app.py`. Test: `pytest tests/ -v`.
- No GitHub push has been done yet as of Milestone 1 — everything is
  local to `main` in the real project folder.
