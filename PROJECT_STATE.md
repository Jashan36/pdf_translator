# Project State

Read this before making any change. Update it after every milestone or
significant decision. This is the working memory that replaces "one
giant prompt" — see CLAUDE.md's development protocol.

## Current milestone

**Milestone 5 — Translation Engine Integration: DONE with one open
item (2026-09-08).** Definition-of-Done items 1-9, 11-17 met. Item 10
("language pairs experimentally exercised where the environment
supports it") is NOT met — see "Open item" below, tracked honestly
rather than marked done.

### Completed components

`core/translation/`:
- `registry.py` — `LANGUAGES` (en/hi/te/ta/kn/ml), FLORES-200 model
  codes reused from Milestone 1's verified research (not re-derived),
  script/font mapping. `Backend.supported_languages()` remains the
  actual authority, not the registry.
- `models.py` — `TranslationRequest`/`TranslationResult`/
  `TranslationContext`/`TranslationErrorCode` (10 structured codes,
  point 12). `confidence` stays `None` unless a backend genuinely
  reports one — never invented.
- `backend.py` — `TranslationBackend` Protocol (`translate`/
  `translate_batch`/`supported_languages`/`backend_info`),
  `TranslationBackendUnavailableError`.
- `mock_backend.py` — `MockTranslationBackend`: deterministic lookup
  table, zero model dependencies. Unknown text gets a clearly-marked
  `[[lang]] text` fallback, never a fake-looking translation.
- `protected_entities.py` — regex-based URL/email/currency/date/number
  protect+restore (point 6), explicitly NOT full NER — a stated v1
  scope boundary.
- `units.py` — `TranslationUnit`, one per TEXT block, carrying every
  member span's id (the "Total"/"₹"/"1500" non-fragmentation example
  from point 5, satisfied by construction).
- `splitting.py` — `UnitSplitter`: sentence-boundary (incl. Devanagari
  `।`) splitting, never truncates; returns `None` (→
  `UNIT_SPLIT_FAILED`) when no safe split exists.
- `service.py` — `TranslationService`: protect → split → ONE batched
  `translate_batch()` call across every segment of every unit → restore
  → quality gates (non-empty, placeholders intact, no stray control
  chars) → exactly one `TranslationResult` per input unit, in order.
- `indictrans2_backend.py` — `IndicTrans2Backend`, isolated (only file
  in the project allowed to import torch/transformers/
  IndicTransToolkit, and only lazily, inside methods). Uses the
  OFFICIAL preprocessing/inference path (`IndicProcessor.preprocess_batch`
  → tokenizer → `model.generate(max_length=256, num_beams=5)` →
  `batch_decode` → `IndicProcessor.postprocess_batch`), fetched via
  WebFetch from AI4Bharat's own `example.py`, not reimplemented.
  `is_available()` capability check; raises
  `TranslationBackendUnavailableError` (never a bare `ImportError`) if
  dependencies are missing.
- `pipeline_bridge.py` — the ONLY connection point to Milestone 4:
  turns successful `TranslationResult`s into ordinary `TranslationInput`s.
  Milestone 4 itself is unmodified.

`docs/research/indictrans2-feasibility.md` — the feasibility gate,
performed first per instructions: environment facts measured directly
(no GPU/CUDA, Windows + WSL Ubuntu present), official requirements
verified via WebFetch (not memory), gate result, and exactly what
would unblock the live experiment.

56 new tests (`test_translation_registry.py` ×7,
`test_translation_models.py` ×4, `test_translation_mock_backend.py` ×7,
`test_translation_protected_entities.py` ×8,
`test_translation_splitting.py` ×6, `test_translation_units.py` ×5,
`test_translation_service.py` ×9,
`test_translation_indictrans2_backend.py` ×6 (1 skipped — appropriately,
per point 20),
`test_translation_pipeline_bridge.py` ×3,
`test_translation_pdf_e2e.py` ×2) — **165 tests passing, 1 appropriately
skipped** (up from 109). Includes a structural test
(`test_full_translation_architecture_uses_no_pymupdf_mutation_apis_directly`)
that parses every `core/translation/*.py` file via `ast` and asserts
none of them call a PDF-mutation API directly — point 19 enforced by
static check, not just code review.

### Feasibility gate result (full detail: `docs/research/indictrans2-feasibility.md`)

- **Native Windows: NOT SUPPORTED** — confirmed via WebFetch against
  IndicTransToolkit's own README ("not meant/built/tested for
  Windows"), not attempted.
- **WSL Ubuntu: hardware-feasible, blocked by environment access.**
  8 cores / 7.6 GiB RAM / 950 GB disk / Python 3.12.3 — genuinely
  adequate for the distilled 200M-parameter model on CPU. But this
  session's WSL image has no `pip`/`ensurepip`/`python3-venv`
  installed, and installing them needs `sudo`, which requires an
  interactive password this non-interactive session doesn't have.
  This is an **access blocker, not a compatibility finding** — per the
  milestone's own instruction not to fight the environment, this was
  reported honestly rather than pursued further.
- Real package/model facts recorded (not from memory): distilled
  checkpoints `ai4bharat/indictrans2-en-indic-dist-200M` /
  `-indic-en-dist-200M`; `numpy>=2.1, torch>=2.5, transformers>=4.51`;
  official `max_length=256` generation cap.

### Open item — Definition-of-Done #10 not met

The live IndicTrans2 benchmark (point 8: 13 sentence categories × 5
language pairs) was **not run** — blocked as above, not skipped
without trying. Tracked as `docs/research/EXPERIMENTS.md` #13, to be
the first thing attempted once environment access allows it (e.g. the
user runs `sudo apt install python3-venv python3-pip` once in their
own interactive WSL session). No code changes are anticipated to be
needed at that point — `IndicTrans2Backend` is already written and
interface-tested against the official API.

### Known limitations discovered during implementation

1. **Multi-span translation units aren't fully wired through Milestone
   4 yet.** `units.py` correctly groups a multi-span line (e.g.
   "Total"/"₹"/"1500") into one translation unit, but
   `pipeline_bridge.py` maps the result onto only the FIRST member
   span's bbox for actual PDF mutation. No current fixture has a
   multi-span line, so this hasn't caused an observed defect, but it's
   a real, documented gap (`docs/research/EXPERIMENTS.md` #14) —
   extending Milestone 4 to support a union-bbox region would be
   needed to fully close it, deliberately not attempted this milestone
   (would be a Milestone 4 redesign).
2. **`UnitSplitter`'s 800-character default is an unverified
   approximation** of IndicTrans2's real 256-token generation cap —
   the two have never been compared against the real tokenizer
   (`docs/research/EXPERIMENTS.md` #15), since no live run was
   possible.
3. **Mock-backend "translated" text can still contain the literal
   source string** when it falls back to the `[[lang]] text` marker
   for anything not in its curated table — this correctly trips
   Milestone 4's `source_text_removed` verification check (confirmed
   while building the end-to-end test, not a bug — the check is
   working as designed). The PDF e2e test uses a curated table entry
   specifically to get a clean pass; this is documented so it isn't
   mistaken for a pipeline defect later.

**Next: either close the open item (run the live IndicTrans2 benchmark
once environment access allows) or proceed to Milestone 6 (Context-
Aware Translation) per the user's direction — Qwen/Ollama/contextual
review remain explicitly NOT integrated, per this milestone's stop
condition.**

---

## Previous milestones

### Milestone 4 — Whole-Document Redact/Reinsert Pipeline: DONE (2026-09-08).

#### Completed components

`core/pipeline/`: `models.py` (`WholeDocumentTranslationRequest`,
`TranslationInput`, `RenderConfig`/`FitConfig`/`MutationConfig`,
`PlannedTranslation`, `TranslationPlan`, `CollisionIssue`,
`VerificationCheck`/`VerificationResult`, `PerformanceTimings`,
`PipelineResult`, `PlanStatus`/`MutationStatus`/`PipelineStatus`),
`planner.py` (`TranslationPlanner` — builds the complete plan, running
Milestone 3's `TextFitEngine` per unit, BEFORE any mutation; resolves
identity purely from the Document Model's `span_id`, never a
positional PyMuPDF index), `validator.py` (`PlanValidator` — point-4
collision/overlap analysis: translated-translated overlaps, expansion
into an untouched source block/image/drawing, page-bounds violations;
only NEWLY introduced overlaps are ever flagged, never a pre-existing
legitimate one), `executor.py` (`MutationExecutor` — the transactional
mutation stage: pre-verify every region before touching anything,
redact all, commit all, reinsert all via the EXISTING `LayoutRenderer`,
save to `.tmp`; source PDF never touched), `verifier.py`
(`DocumentVerifier` — structural + text-layer(absence-only) + pixel
checks, every check tagged with its `category` so none are conflated;
OCR check present as a `skipped` `VerificationCheck` via a clean
`OCRVerifier` protocol, no OCR dependency added), `pipeline.py`
(`TranslationPipeline` — the transactional orchestrator: temp output
only promoted to the real path after verification passes, discarded
otherwise).

`scripts/fixtures/build_pipeline_fixture.py` +
`tests/fixtures/pipeline_multilingual.pdf` — point-10 fixture: English,
Telugu, Hindi, Tamil, Kannada, mixed-script, an image, a vector
drawing, all spatially separated, plus an untouched paragraph for
protected-content testing. Same `insert_text`+`fontfile=` construction
as the Milestone 2 fixture (byte-exact ground truth), for the same
reason (Decision 7's Milestone-2 update).

41 new tests across `test_pipeline_planner.py` (6),
`test_pipeline_validator.py` (8), `test_pipeline_executor.py` (6),
`test_pipeline_verifier.py` (8), `test_pipeline_e2e.py` (13) — **109
tests passing total** (up from 68), covering: multi-block/multi-
language plan generation, plan validation (all 5 collision kinds),
complete mutation, protected-content preservation, geometry
preservation (byte-identical untouched blocks), all 7 of point 12's
failure/rollback cases (NO_FIT, invalid geometry, missing source text,
overlapping regions, page-bounds violation, renderer/missing-font
failure, verification failure), determinism, and stage-level
performance timing.

#### Real bug found and fixed during implementation

The executor's render-time CSS initially omitted `line-height`/
`text-align`, which `TextMeasurer` (Milestone 3) always includes when
fitting. This made `insert_htmlbox` lay out text differently at
mutation time than during fitting — a plan that measured as
`FIT_AFTER_BOTH` then reported "clipped" when actually rendered
(caught immediately by `test_successful_mutation_produces_valid_temp_pdf`,
not shipped silently). Fixed by carrying `line_height`/`alignment`
through `PlannedTranslation` (set by the planner from `RenderConfig`)
so the executor's render CSS is byte-identical to what
`TextFitEngine`/`TextMeasurer` actually measured. **Lesson recorded in
`ARCHITECTURE_DECISIONS.md` Decision 14: any config affecting
`insert_htmlbox` layout must travel with the plan, not be re-derived
at mutation time — a divergence there silently invalidates the fit
decision.**

#### Experimentally observed behavior (not claimed, measured)

Whole-document pipeline, 5 blocks / 1 page (Telugu, Hindi, Tamil,
Kannada, mixed): **656.6ms total, 131.3ms/block average** — planning+
fit 365.0ms (73ms/block), validation 0.5ms (negligible), mutation
142.8ms, verification 148.2ms (the priciest stage after planning+fit:
re-opens 2-3 PDF handles, re-extracts the output document, renders
per-region pixmaps). Not yet tested at real multi-page/many-block
scale — see `docs/research/EXPERIMENTS.md` #11.

#### Remaining / open questions (not resolved here)

- **Whole-document scale untested** (Experiment #11) — only 1 page / 5
  blocks measured.
- **Two-layer collision defense only exercised via synthetic/injected
  plans in tests, not organic multi-block competition on a dense real
  page** (Experiment #12) — both e2e collision tests use a stub
  planner to inject a guaranteed collision, because Milestone 3's own
  fit-time obstacle avoidance already prevents naive collisions from
  occurring organically on the current (spatially generous) fixture.
- **Verification cost may not scale linearly** — currently re-extracts
  and re-checks the FULL output document regardless of how few blocks
  changed; a targeted "only touched pages" optimization is deferred
  until Experiment #11 shows it's actually needed.
- **No translation engine at the time** — `TranslationInput` was
  fixture/test-supplied only. **Now addressed, see Milestone 5 above**
  (with one open item: the live IndicTrans2 benchmark).

### Milestone 3 — Automatic Text-Fit Engine: DONE (2026-09-08).

#### Completed components

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

#### Experimentally observed behavior (not claimed, measured)

- Fit-engine cost across the 15 fixture cases: **339ms total, 22.6ms/
  block average** (range ~6.5ms single-attempt fit to ~43ms an
  8-attempt binary search) — see `docs/research/EXPERIMENTS.md` #10.
  Acceptable for a local Streamlit app at the scale tested; whole-document
  scale (hundreds of blocks) not yet tested at the time (now partly
  addressed in Milestone 4 above, still not at full scale).
- Binary search converges within its 20-iteration cap on every fixture
  case tested (typically 6-8 attempts to converge from an 18pt→6pt
  range at a 0.5pt step) — never needed the full cap in this pass.

#### Remaining components / open questions (explicitly not resolved here)

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
- **Whole-document application not built at the time** — this
  milestone fit ONE block/span per `TextFitEngine.fit()` call; a
  pipeline that plans every block on a page/document, applies all
  edits, and only then re-extracts (per known limitation #2 below) was
  Milestone 4's job — **now DONE, see Milestone 4 above.**
- **No new dependencies were needed** — `pymupdf`/`pydantic` already
  covered everything; `docs/dependencies.md` unchanged this milestone.

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
session's "Milestone 3" built the deterministic text-fit engine,
"Milestone 4" built its whole-document application (plan/validate/
mutate/verify), and "Milestone 5" built the backend-independent
translation architecture (mock backend fully working; IndicTrans2
adapter code-complete but not yet run against a real model — see the
open item above).

1. ✅ PDF Forensics (`PDF → inspect → JSON`)
2. ✅ Document Model + single-block redact/reinsert proof (this session)
3. ✅ Automatic text-fit engine (geometry tolerance → binary-search
   font reduction → structured NO_FIT; this session)
4. ✅ Whole-document redact/reinsert pipeline (`core/pipeline/`;
   extract once, plan everything via the text-fit engine, validate
   collisions, mutate in one transactional pass, verify — never
   interleave extract/edit/re-extract, per Milestone 2's known
   limitation #2).
5. ✅ Translation engine integration (`core/translation/`; backend
   abstraction, mock backend, IndicTrans2 adapter code-complete but
   unexercised — live benchmark still open, `EXPERIMENTS.md` #13)
5b. ⬜ Language detection
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
- `core/pipeline/` — Milestone 4's whole-document pipeline
  (`models.py`, `planner.py`, `validator.py`, `executor.py`,
  `verifier.py`, `pipeline.py`). Entry point:
  `pipeline.TranslationPipeline().run(request)`.
- `core/translation/` — Milestone 5's translation layer (`registry.py`,
  `models.py`, `backend.py`, `mock_backend.py`, `protected_entities.py`,
  `units.py`, `splitting.py`, `service.py`, `indictrans2_backend.py`,
  `pipeline_bridge.py`). Feeds `core/pipeline/` via `pipeline_bridge.py`
  only — never mutates a PDF itself.
- `docs/research/indictrans2-feasibility.md` — the Milestone 5
  feasibility gate (environment facts, official requirements, gate
  result, unblock conditions).

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
