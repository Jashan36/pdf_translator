# Dependencies

Running log of verified dependencies for this project. Every entry
must be checked against the `dependency-verification` skill before
being added — see `.claude/skills/dependency-verification/SKILL.md`.
Staging (CURRENT / NEXT MILESTONE / FUTURE / OPTIONAL) reflects the
research in `docs/research/` — see `docs/research/ARCHITECTURE_DECISIONS.md`
for the reasoning behind each. Do NOT install FUTURE/OPTIONAL entries
merely because they're researched here.

---

## CURRENT (installed, Milestone 1)

### streamlit
- Version: 1.63.0 (installed; `requirements.txt` pins `>=1.38`)
- Purpose: local UI — upload, selectors, previews, downloads.
- License: Apache-2.0
- Official URL: https://github.com/streamlit/streamlit
- Why required: Master plan Section 4.1 — no separate frontend needed.
- Milestone introduced: 1.
- Alternative: none seriously considered (matches master plan's own
  recommendation).
- Risk: none identified. Note (research): no documented async/threading
  guidance for long-running inference calls (`docs/research/streamlit.md`)
  — relevant once OCR/translation inference is added (Milestone 5+),
  not now.
- Verified: 2026-09-08 via local `pip install` + `streamlit.__version__`.

### pymupdf
- Version: 1.28.2 (installed; `requirements.txt` pins `>=1.24`)
- Purpose: PDF extraction, geometry, rendering, and (from Milestone 2)
  text insertion.
- License: AGPL-3.0 (commercial license available from Artifex) —
  **flag for the user**: this repo has no LICENSE file yet; AGPL's
  copyleft terms should be reviewed before any distribution,
  especially if ever hosted as a service. Confirmed via WebFetch
  against PyMuPDF's own GitHub README (2026-09-08).
- Official URL: https://github.com/pymupdf/PyMuPDF
- Why required: Master plan Section 4.2 — span-level extraction +
  rendering + (research-confirmed) the only shaping-capable text
  insertion path (`insert_htmlbox`) for Indic scripts.
- Milestone introduced: 1 (extraction); Milestone 2 will start using
  its insertion/redaction APIs.
- Alternative: none found offering the same extraction+insertion+
  rendering combination (`docs/research/pymupdf.md`).
- Risk: font `flags` metadata can be wrong/incomplete (documented by
  PyMuPDF itself; already mitigated in `_font_from_span`). Classic
  text-insertion APIs (`insert_text`/`insert_textbox`/`TextWriter`)
  **must not be used for Indic scripts** — use `insert_htmlbox`
  exclusively (confirmed via PyMuPDF maintainers, `docs/research/pdf-typography.md`).
- Verified: 2026-09-08 via local `pip install` + version check +
  research pass.

### pydantic
- Version: 2.13.5 (installed; `requirements.txt` pins `>=2.7`)
- Purpose: typed internal Document model (`core/models.py`).
- License: MIT
- Official URL: https://github.com/pydantic/pydantic
- Why required: Master plan Section 64 — typed model over untyped
  dicts.
- Milestone introduced: 1.
- Alternative: plain `dataclasses` (rejected — no validation).
- Risk: none identified.
- Verified: 2026-09-08 via local `pip install` + version check.

### pytest (dev-only, not in requirements.txt)
- Purpose: regression tests against fixture PDFs.
- License: MIT
- Official URL: https://github.com/pytest-dev/pytest
- Why required: Master plan Section 54.
- Milestone introduced: 1.
- Alternative: `unittest` (rejected — pytest is the project convention).
- Risk: none identified.
- Verified: 2026-09-08 via local `pip install`.

---

## NEXT MILESTONE (Milestone 2 — Exact Text Replacement, no new pip installs expected)

No new dependencies are required for Milestone 2 — it uses PyMuPDF's
existing redaction (`add_redact_annot`/`apply_redactions`) and
insertion (`insert_htmlbox` for any Indic-script test content)
APIs, already installed. The Milestone 2 experiment plan
(`docs/research/EXPERIMENTS.md` #1) should download at least one Noto
font per target script as a **project asset**, not a pip dependency —
see the `fonts/` directory in the master plan's Section 52 structure.

### Noto Sans (Telugu / Devanagari / Tamil / Kannada / Malayalam)
- Purpose: target-script rendering fonts for `insert_htmlbox`.
- License: OFL 1.1 (open, embeddable) — confirmed via the official
  `notofonts` GitHub org LICENSE file.
- Official URL: https://github.com/notofonts/{telugu,devanagari,tamil,kannada,malayalam}
- Why required: Master plan Section 22 — original fonts don't contain
  Indic glyphs; research (`docs/research/pdf-typography.md`) confirms
  these are the correct open-license fallback fonts.
- Milestone introduced: 2 (needed for the shaping experiment) / 3
  (needed for real rendering).
- Alternative: any other OFL/open-licensed font with full Indic
  OpenType tables for the target script — not evaluated, Noto is the
  master plan's own recommendation and is confirmed available.
- Risk: `insert_htmlbox` "needs a font with correct OpenType tables for
  the target script, or it can still fragment glyphs" per PyMuPDF's own
  maintainers — must verify empirically per script (Experiment 1), not
  assume any Noto variant works out of the box.

---

## FUTURE (later milestones — researched, NOT installed)

### PaddleOCR (v3.x, PP-OCRv5/v6)
- Purpose: OCR for scanned/Class-B PDFs.
- License: see `docs/research/ocr.md` (confirmed via official repo).
- Official URL: https://github.com/PaddlePaddle/PaddleOCR
- Why required: Master plan Section 15/48 — only for scanned PDFs.
- Milestone introduced: 7 (OCR), not before.
- Alternative: docTR (Apache-2.0), EasyOCR.
- Risk: **does not support Kannada or Malayalam recognition** — a real
  gap against this project's target language list. Needs EasyOCR as a
  secondary path for Kannada; Malayalam has no confirmed OCR path
  among the three engines checked (`docs/research/ocr.md`,
  `docs/research/EXPERIMENTS.md` #7).

### EasyOCR
- Purpose: OCR fallback specifically for Kannada (PaddleOCR gap).
- License: see `docs/research/ocr.md`.
- Official URL: https://github.com/JaidedAI/EasyOCR
- Why required: Covers Kannada where PaddleOCR doesn't.
- Milestone introduced: 7.
- Alternative: docTR (also checked, no Malayalam either).
- Risk: weaker general accuracy reputation than PaddleOCR (not
  independently benchmarked in this research pass).

### Docling
- Purpose: optional structural analyzer for complex documents
  (tables, multi-column layouts).
- License: MIT (confirmed via official repo LICENSE).
- Official URL: https://github.com/docling-project/docling
- Why required: Master plan Section 16 — complex-document fallback
  only, not primary parser.
- Milestone introduced: 8 (Tables and Complex Layout), only if
  PyMuPDF-based structure inference proves insufficient.
- Alternative: PP-StructureV3 (bundled with PaddleOCR/PaddleX — arrives
  more naturally alongside OCR in Phase 7).
- Risk: exact bbox schema (`docling-core`) UNVERIFIED in this research
  pass — inspect directly before integrating.

### IndicTrans2 (+ CTranslate2)
- Purpose: primary Indic-language translation engine.
- License: see `docs/research/indictrans2.md` (confirmed via official
  repo/model cards).
- Official URL: https://github.com/AI4Bharat/IndicTrans2
- Why required: CLAUDE.md's translation rule; purpose-built for Indic
  languages with published per-language benchmarks.
- Milestone introduced: 5 (Translation Provider), pending Experiment 6
  (Windows/WSL2 feasibility).
- Alternative: Google Cloud Translation (cloud, costs money), Argos
  Translate (offline, lower quality), Gemini API (contextual only).
- Risk: **non-uniform quality** — Hindi outperforms Telugu/Tamil/Kannada
  per official benchmark paper (via secondary source, flagged for
  re-verification). CPU/RAM requirements not officially documented —
  needs Experiment 3/4 benchmarking on real hardware.

### IndicTransToolkit
- Purpose: required preprocessing/tokenizer wrapper for IndicTrans2's
  HuggingFace inference path.
- Version: 1.1.1 (PyPI)
- License: MIT
- Official URL: https://github.com/VarunGumma/IndicTransToolkit
  (**not** an official AI4Bharat repo — community-maintained, but
  directly used by AI4Bharat's own official example code)
- Why required: AI4Bharat's own `example.py` imports `IndicProcessor`
  from it directly.
- Milestone introduced: 5, pending Experiment 6.
- Alternative: the separate fairseq inference path (avoids this
  dependency, less-documented/less-common).
- Risk: **explicitly not built/tested for Windows** per its own
  README — this project's dev environment is Windows. Needs
  Experiment 6 (WSL2/Docker feasibility) before committing to this
  path as anything more than optional/advanced.

### Ollama + Qwen3
- Purpose: contextual reasoning — translation review, terminology
  extraction, semantic classification, context summarization. NOT the
  primary translator.
- License: Apache-2.0 (confirmed via official Qwen3 repo/blog).
- Official URL: https://ollama.com/library/qwen3,
  https://github.com/QwenLM/Qwen3
- Why required: CLAUDE.md's stance, confirmed by research — Qwen3
  claims broad language *coverage* but has no published Indic
  translation *quality* benchmark, so it stays out of the primary role.
- Milestone introduced: 6 (Context Engine).
- Alternative: Gemini API (cloud, opt-in only per privacy rule).
- Risk: model-size/hardware tradeoff unresolved (which of `0.6b`
  through `235b` is practical on target hardware) — no experiment
  defined yet for this specifically; add one when Milestone 6 begins.

### pytesseract (+ system Tesseract install)
- Purpose: OCR-based visual QA bridge check (catches mis-shaped/garbled
  glyphs that pass structural checks but fail visually).
- License: Apache-2.0 (confirmed via official repo).
- Official URL: https://github.com/madmaze/pytesseract
- Why required: Decision 9 (`ARCHITECTURE_DECISIONS.md`) — directly
  motivated by the Indic-shaping risk found in this research.
- Milestone introduced: 9 (Visual QA).
- Alternative: none evaluated — this is a thin wrapper around the
  standard Tesseract OCR engine.
- Risk: requires a separate system-level Tesseract install, not pure
  pip — a new install-complexity surface to document when Phase 9 is
  reached.

### scikit-image
- Purpose: SSIM-based comparison for protected-region visual QA.
- License: BSD-3-Clause (standard for scikit-image; not independently
  re-verified in this pass — verify at install time).
- Official URL: https://scikit-image.org/
- Why required: Decision 9 — SSIM tolerates rendering anti-aliasing
  noise better than raw pixel diff (confirmed via official API docs).
- Milestone introduced: 9.
- Alternative: raw pixel diff alone (rejected — master plan Section 37
  already warns against this).
- Risk: none identified beyond standard scientific-Python stack size.

---

## OPTIONAL (may never be needed — revisit only if a specific gap appears)

### uharfbuzz (direct HarfBuzz Python binding)
- Purpose: manual text shaping if `insert_htmlbox` ever proves
  insufficient for a specific script/font combination.
- Why NOT current: PyMuPDF already ships HarfBuzz-backed shaping via
  `insert_htmlbox` — a manual integration would duplicate that at
  higher complexity (Decision 7).
- Revisit condition: Experiment 1 (`EXPERIMENTS.md`) finds a script
  `insert_htmlbox` cannot shape correctly even with a correct Noto
  font.

### LibreTranslate
- Purpose: self-hosted translation API wrapper over Argos.
- Why NOT current: master plan Section 12.2 itself notes direct Argos
  integration is simpler for a purely local app; not re-evaluated in
  this research pass beyond confirming that reasoning still holds.
- Revisit condition: only if a multi-user / networked deployment
  scenario emerges (contradicts current local-single-app scope).

### Google Cloud Translation / Gemini API
- Purpose: cloud-based "Standard"/"Contextual" translation modes.
- Why NOT current: master plan Section 33/34 — free/offline-first
  operation is the default; these are opt-in, not required for MVP.
- Revisit condition: Milestone 5, if the user wants a cloud-quality
  option alongside IndicTrans2, or if Experiment 6 shows IndicTrans2 is
  not viably deployable on Windows.

### Argos Translate
- Purpose: fully offline, no-API-key translation fallback.
- Why NOT current: not yet needed; Milestone 5 hasn't started.
- Revisit condition: Milestone 5, as the "Private/Offline" mode
  fallback (master plan Section 29 Mode 3) or as the IndicTrans2
  fallback if Experiment 6 fails.
