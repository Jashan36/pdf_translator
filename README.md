# Local PDF Localizer

Local-first tool to translate the text in a PDF into another language
while preserving its original visual design (layout, fonts, images,
colors, geometry). Full architecture and rationale live in
[local_pdf_localizer_technical_master_plan.md](local_pdf_localizer_technical_master_plan.md) —
read that first.

> AI decides what the text should say. Deterministic PDF code decides
> where and how it's rendered. See "Core principle" in the master plan.

## Status

**Milestone 1 — PDF Forensics.** The app can upload a native-text PDF,
extract its structure (pages, text spans with bbox/font/color, images)
via PyMuPDF, and display it — no translation yet. This proves the
extraction layer before anything is built on top of it (master plan,
Section 69).

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Test

```bash
pip install pytest
pytest tests/ -v
```

## Project layout

```text
app.py                    Streamlit UI
core/models.py            Internal Document model (Section 5)
core/pdf/analyzer.py       PDF -> Document extraction (Phase 1)
tests/fixtures/            Test PDFs
tests/test_extraction.py   Milestone 1 regression tests
```

Structure grows with each milestone in the master plan (Section 52/53) —
we don't scaffold `translation/`, `ocr/`, `layout/`, `qa/` etc. until the
milestone that needs them.

## Roadmap (from the master plan)

1. **PDF Forensics** — inspect and model a PDF (this milestone).
2. Exact text replacement (manual translation, prove PDF engineering
   works before adding AI).
3. Automatic text-fit engine (shrink/wrap/warn).
4. Language detection.
5. Translation provider integration (Google Cloud Translation first,
   Argos as offline fallback).
6. Context-aware (paragraph-level) translation.
7. OCR for scanned PDFs.
8. Tables and complex layout.
9. Visual + semantic QA.
10. Family-friendly UI polish.
