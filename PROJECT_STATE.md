# Project State

Read this before making any change. Update it after every milestone or
significant decision. This is the working memory that replaces "one
giant prompt" — see CLAUDE.md's development protocol.

## Current milestone

**Milestone 1 — PDF Forensics: DONE.**

- `core/models.py` — internal Document model (master plan Section 5).
- `core/pdf/analyzer.py` — PyMuPDF-based extraction: page geometry,
  text spans (bbox/font/size/bold/italic/color/rotation), images,
  native-text-vs-scanned heuristic.
- `app.py` — Streamlit UI: upload → inspect → JSON export. No
  translation yet.
- `tests/test_extraction.py` — 4 passing tests against
  `tests/fixtures/sample_native.pdf`.

**Next: Milestone 2 — Exact Text Replacement** (master plan Section 43).
Manually-supplied translation (no AI) replacing text in-place while
keeping the same PDF layout. Purpose: prove the PDF-engineering/
rendering path works before any translation model touches it.

**Milestone 2 must include, per the research pass below:** using
`page.add_redact_annot`/`apply_redactions` (not a visual overlay) to
remove original text, then `page.insert_htmlbox()` — never
`insert_text`/`insert_textbox` — for reinsertion, with at least one
Indic-script test case (Noto font) to validate shaping works before
calling the milestone done (`docs/research/EXPERIMENTS.md` #1).

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

## Milestone roadmap (master plan Section 53)

1. ✅ PDF Forensics (`PDF → inspect → JSON`)
2. ⬜ Exact text replacement (`PDF → replace text → PDF`, no AI)
3. ⬜ Automatic text-fit engine (shrink → wrap → warn)
4. ⬜ Language detection
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
  `ARCHITECTURE_DECISIONS.md` (12 synthesized decisions),
  `SOURCES.md` (aggregated citations), and `EXPERIMENTS.md` (7
  empirical validations still needed — read before assuming a
  research finding is final).

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
