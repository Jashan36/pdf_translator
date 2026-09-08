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

## Open decisions (not yet made — do not assume)

- **Translation provider for Milestone 5+**: undecided. Candidates:
  Google Cloud Translation (doc's recommended first experiment),
  Argos Translate (offline), IndicTrans2 (best Indic quality,
  recommended primary per CLAUDE.md once we reach that stage), Gemini
  API (contextual mode). Do not pick one without asking the user or
  running the `technical-research` skill first.
- **OCR backend**: undecided (PaddleOCR is the plan's primary
  candidate). Not needed until Milestone 7.
- **Full technical research pass**: not yet run. The user proposed a
  broad research pass (PyMuPDF, PaddleOCR, IndicTrans2,
  IndicTransToolkit, Ollama, Qwen3, PDF typography, visual-QA methods,
  Streamlit) to be written to `docs/research/`. Ask before running
  this — it's a large task; better to research each dependency when
  its milestone is actually reached, using the `technical-research`
  skill, unless the user wants it front-loaded.

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
- `docs/dependencies.md` — running log of verified dependencies
  (created by the `dependency-verification` skill).
- `docs/research/` — technical research notes, created lazily as
  needed (see "Open decisions" above), not all up front.

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
