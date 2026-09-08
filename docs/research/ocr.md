# OCR Research — PaddleOCR current architecture, and alternatives

Date checked: 2026-09-08
Scope: master plan Section 15 (OCR Strategy) and Section 48 (Phase 7 — OCR).
Rule followed: no claim below is from training-data memory; every claim
was checked against a live fetch of an official source on 2026-09-08.
Where a fetch tool's summary could not be fully trusted (e.g. content
truncation), that is noted explicitly.

## 1. Current PaddleOCR major version and headline components

**Confirmed.** PaddleOCR is currently on the **3.x major version line**,
with the latest tagged release **v3.7.0** (released 2026-06-11) per the
project's GitHub Releases page. Recent release history: v3.7.0 (PP-OCRv6),
v3.6.0 (PaddleOCR-VL-1.6), v3.5.0, v3.4.1, v3.4.0 (PaddleOCR-VL-1.5).
Source: https://github.com/PaddlePaddle/PaddleOCR/releases

The project owner's warning about stale 2.x knowledge is **justified**:
the Python API changed. Current API uses `PaddleOCR(...).predict(input, ...)`
returning `Result` objects with `dt_polys` / `rec_texts` / `rec_scores` /
`rec_polys` / `rec_boxes`, not the 2.x-era `ocr.ocr(img, cls=True)` call
pattern (which several secondary/community sources still show — treat
those as stale). Source:
https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md

Headline pipeline components, all verified as real, currently-shipping
components on the official repo/docs (not assumed from the name alone):

- **PP-OCRv6** — the current-generation detection+recognition system
  (released with v3.7.0, 2026-06-11). Built on a "PPLCNetV4" backbone,
  three size tiers (tiny/small/medium), claimed "+4.6% detection /
  +5.1% recognition" accuracy over PP-OCRv5, single model unifying 50
  languages. Source: https://github.com/PaddlePaddle/PaddleOCR/releases
- **PP-OCRv5** — the prior-generation detection+recognition system,
  still documented and still the recommended path for some
  script-specific recognition models (see language section below).
  Source: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5.md
- **PP-StructureV3** — layout/table/formula/reading-order structure
  pipeline (confirmed real and current; see Section 3 below).
- **PaddleOCR-VL** — a real, current, separately-published vision-language
  document-parsing model (0.9B params, current version PaddleOCR-VL-1.6).
  This is NOT a hallucinated name: it has its own official Hugging Face
  model card and is referenced in the PaddleOCR release notes.
  Source: https://huggingface.co/PaddlePaddle/PaddleOCR-VL and
  https://github.com/PaddlePaddle/PaddleOCR/releases

**Conclusion on the names the project owner flagged**: PP-OCRv5,
PP-OCRv6, PaddleOCR-VL, and PP-StructureV3 are all **real, verified,
currently-shipping** components of PaddleOCR 3.x as of the 2026-06-11
v3.7.0 release. None of these names should be treated as invented.

## 2. Text detection/recognition capability, bounding boxes, confidence

Confirmed via the official pipeline usage doc
(https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md):

- `dt_polys`: detection polygons, 4-vertex numpy arrays per detected
  text region, with `dt_scores` as the corresponding detection
  confidence.
- `rec_texts` / `rec_scores`: recognized text strings and their
  confidence, filtered by a configurable `text_rec_score_thresh`.
- `rec_polys`: the polygons matching the recognized (kept) text.
- `rec_boxes`: axis-aligned rectangular boxes, shape `(n, 4)`,
  `int16`, format `[x_min, y_min, x_max, y_max]` — this is the
  simplest bbox format for downstream layout reconstruction.

This is exactly the geometry data this project would need (bounding
box + text + confidence) if/when OCR is added.

## 3. Layout / table / formula recognition, reading order

Confirmed via PaddleX pipeline docs (PaddleX is Baidu's official
inference framework that PaddleOCR 3.x's structure pipelines run on):
https://paddlepaddle.github.io/PaddleX/3.3/en/pipeline_usage/tutorials/ocr_pipelines/PP-StructureV3.html

PP-StructureV3 provides, in one pipeline:

- **Layout detection** — classifies/locates regions (text, table,
  image, title, etc.)
- **Reading order restoration** — explicitly restores multi-column
  reading order for Markdown export.
- **Table recognition** — converts detected tables to HTML/structured
  form, exportable to XLSX.
- **Formula recognition** — extracts math formulas.
- **OCR** — underlying text detection/recognition across the page.

JSON output includes `block_bbox` (per-layout-region bounding box),
`dt_polys`/`rec_polys` (per-text-line polygons), and `block_id` /
`block_order` (explicit reading-order indices) — i.e. coordinate data
survives into the structured JSON output, not just the Markdown.

PaddleOCR-VL-1.6 (the VLM alternative to the PP-StructureV3 pipeline)
is reported at "96.3% accuracy on OmniDocBench v1.6" per its Hugging
Face model card and the PaddleOCR release notes — this is the
project's own benchmark claim, not independently verified here, and
should be treated as a vendor-reported number.
Source: https://huggingface.co/PaddlePaddle/PaddleOCR-VL

## 4. Multilingual support — Telugu/Hindi/Tamil/Kannada/Malayalam

This is the most important and most nuanced finding. Checked directly
against the current PP-OCRv5 multilingual recognition-model table:
https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md
(fetched via raw GitHub content, 2026-09-08)

Current PP-OCRv5 script-family recognition models, as documented:

| Model | Languages covered |
|---|---|
| `devanagari_PP-OCRv5_mobile_rec` | Hindi, Marathi, Nepali, Bihari, Maithili, Bhojpuri, Magahi, Newari, Konkani, Sanskrit, Haryanvi, English |
| `ta_PP-OCRv5_mobile_rec` | Tamil, English |
| `te_PP-OCRv5_mobile_rec` | Telugu, English |

The document states PP-OCRv5 covers **106 languages** in total, but
**Kannada and Malayalam do not appear anywhere in this document** — not
under their own model, and not grouped into another script family's
model list. This was cross-checked against the same repo's legacy
2.x-era language table
(`docs/version2.x/ppocr/blog/multi_languages.en.md`, ~80 languages
listed by code) and **Kannada and Malayalam are absent there too**.

**Verified conclusion: Telugu, Hindi, and Tamil are currently supported
by official PaddleOCR (PP-OCRv5) recognition models. Kannada and
Malayalam are NOT supported by any current or legacy PaddleOCR
recognition model found in the official repo.** This is a material gap
against the project's target language set and should be flagged for
whoever picks up OCR work later — do not assume PaddleOCR alone will
cover all five priority languages.

The official docs give **no statement** about mixed-language-per-page
handling — this is UNVERIFIED. The architecture (one recognition model
per script family, selected via a `lang=` parameter) suggests
single-script-per-invocation is the default operating mode, but a
document could in principle be OCR'd once per script/region if regions
are pre-classified; this was not confirmed in official docs and should
not be assumed. Mark as UNVERIFIED.

## 5. PDF input support

Confirmed: the `predict()` API in the OCR pipeline doc accepts a PDF
path directly (also images, directories, numpy arrays). Default
behavior processes only the first 10 pages of a PDF/multi-page TIFF
unless reconfigured. Source:
https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md
So OCR pipelines work on page **images** rendered from the PDF
internally — this is image-based OCR, appropriate for the scanned-PDF
fallback path, not a substitute for native-text extraction.

## 6. Installation, license, Python API basics

- **Install**: `pip install paddleocr` (also requires PaddlePaddle
  ≥3.0 as a dependency, per official docs). Sources:
  https://www.paddleocr.ai/latest/en/version3.x/quick_start.html (via
  search-result excerpt) and the PyPI project page.
- **License**: Apache License 2.0, confirmed by fetching the repo's
  `LICENSE` file directly.
  Source: https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE
- **Basic current API** (verified, not 2.x style):
  ```python
  from paddleocr import PaddleOCR
  ocr = PaddleOCR(lang="hi")  # or "ta", "te", etc.
  result = ocr.predict("page.pdf")
  ```
  Constructor also exposes `use_doc_orientation_classify`,
  `use_doc_unwarping`, `use_textline_orientation`,
  `text_detection_model_name`, `text_recognition_model_name`,
  `ocr_version` (e.g. `"PP-OCRv6"`), `device`. Source:
  https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md
  NOTE: `use_angle_cls=True` / `.ocr(img, cls=True)` seen in many
  tutorials and even in one of this research pass's own intermediate
  fetch summaries is the **old 2.x API** — do not use it if/when this
  is implemented; verify against the doc above again at
  implementation time since the API surface has changed across 3.x
  minor releases.

## 7. Alternatives

### docTR (Mindee)
- Repo: https://github.com/mindee/doctr — two-stage detector+recognizer,
  returns nested Page→Block→Line→Word structure with bounding boxes and
  confidence scores.
- Direct PDF support: `DocumentFile.from_pdf(...)`.
- License: Apache 2.0.
- Local execution: yes, pip-installable, GPU optional.
- **Language support: the official README does not mention Telugu,
  Hindi, Tamil, Kannada, Malayalam, or Indic scripts at all.** This is
  a real gap for this project's priority languages and was not found
  anywhere in the fetched README. UNVERIFIED beyond "not mentioned" —
  a deeper look at docTR's model zoo would be needed before ruling it
  out completely, but on the primary official source it does not
  appear to target Indic scripts.

### EasyOCR (JaidedAI)
- Repo: https://github.com/JaidedAI/EasyOCR — official language list at
  https://www.jaided.ai/easyocr/ confirms: **Telugu (`te`), Hindi
  (`hi`), Tamil (`ta`), and Kannada (`kn`) are all explicitly
  supported.** Malayalam is **not** in the official language list —
  confirmed absent by direct inspection of the official language table.
- Returns bounding boxes and confidence scores per detected text
  region.
- PDF input: **not supported directly** — the documented input types
  are file path / OpenCV image / bytes / URL, all image-oriented.
  A PDF page would need to be rendered to an image first (e.g. via
  PyMuPDF) before handing it to EasyOCR.
- License: Apache 2.0.
- Latest tagged release found: v1.7.2 (2024-09-24) — this is
  considerably older than PaddleOCR's active 2026 release cadence;
  treat EasyOCR as slower-moving/less actively developed by comparison,
  though still functional and Apache-licensed.

### Language-coverage comparison for this project's 5 priority languages

| Language | PaddleOCR (PP-OCRv5) | EasyOCR | docTR |
|---|---|---|---|
| Telugu | Yes (`te`) | Yes (`te`) | Not mentioned |
| Hindi | Yes (via `devanagari` model) | Yes (`hi`) | Not mentioned |
| Tamil | Yes (`ta`) | Yes (`ta`) | Not mentioned |
| Kannada | **No** | Yes (`kn`) | Not mentioned |
| Malayalam | **No** | **No** | Not mentioned |

**Malayalam is not confirmed supported by any of the three OCR engines
checked in their official docs.** This should be flagged as an open
risk for later OCR work — do not assume it will "just work" with any
of these tools; it needs its own targeted research pass when OCR
becomes the active milestone.

## 8. Does this project need OCR now?

**No — per the master plan itself (Sections 15 and 48) and per this
project's CLAUDE.md milestone discipline, OCR is only needed for the
scanned-PDF fallback path, which is Phase 7, strictly after native-text
PDFs (PyMuPDF path) are working.** This research pass confirms the
plan's own architecture is sound and does not surface any reason to
pull OCR forward:

- Native-text PDFs need no OCR at all (PyMuPDF reads real text objects
  directly with exact geometry).
- OCR is inherently lossier and slower, and (per Section 4 above) has
  real, currently-unresolved language-coverage gaps for this project's
  own priority list (Kannada, Malayalam) that would need to be solved
  before OCR could be trusted for those languages.

**Recommendation: do NOT add PaddleOCR (or docTR/EasyOCR) as a project
dependency yet.** This is a **future** dependency for Phase 7 only.
The correct integration point, matching the master plan's own diagram
(Section 48) and this file's findings, is:

```text
detect native text (PyMuPDF)
   ├── yes → PyMuPDF extraction (current milestone path)
   └── no  → OCR fallback (PaddleOCR PP-OCRv5/v6 recognition models,
             selected per detected/declared script; EasyOCR as a
             secondary path specifically for Kannada, which current
             PaddleOCR does not cover) → bounding boxes → translation → rendering
```

When Phase 7 is actually reached, re-run this research (per the
technical-research skill's freshness expectation) since PaddleOCR is
on an active ~monthly release cadence (v3.4.0 → v3.7.0 across
2026-01 to 2026-06) and the API/model lineup may have moved again.

## What could NOT be verified

- Whether PaddleOCR supports true mixed-language OCR within a single
  page/call (UNVERIFIED — no official statement found).
- Whether PP-StructureV3's 96.3%-class benchmark figures are
  independently reproducible (these are vendor-reported numbers from
  the official model card/release notes, not verified here).
- docTR's full model zoo was not exhaustively checked beyond the main
  README — it's possible community-contributed Indic-script models
  exist that the README doesn't surface; UNVERIFIED, would need a
  dedicated pass on docTR's own docs site if docTR becomes a
  candidate.
- Exact current pip install / quick-start code block from the
  PaddleOCR README could not be fetched verbatim (GitHub's rendered
  README pointed to the external docs site rather than inlining a
  code sample); the install command and API shown here come from the
  version3.x quick-start/pipeline docs instead, which are official but
  a different page than the bare README.

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| PaddleOCR | Official GitHub repo | https://github.com/PaddlePaddle/PaddleOCR | Official GitHub repo | 2026-09-08 | 3.x (latest v3.7.0) | Current major version, Apache-2.0, pipeline overview |
| PaddleOCR | Releases | https://github.com/PaddlePaddle/PaddleOCR/releases | Official GitHub repo | 2026-09-08 | v3.7.0 (2026-06-11) | Confirms PP-OCRv6/PaddleOCR-VL-1.6 are real, current releases |
| PaddleOCR | LICENSE | https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE | Official GitHub repo | 2026-09-08 | n/a | Apache License 2.0 confirmed |
| PaddleOCR | OCR.en.md (pipeline usage) | https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md | Official docs (repo) | 2026-09-08 | version3.x | Current Python API (`predict()`), bbox/confidence output fields, PDF page limit |
| PaddleOCR | PP-OCRv5_multi_languages.en.md | https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md | Official docs (repo) | 2026-09-08 | PP-OCRv5 | Confirms Telugu/Tamil/Hindi(Devanagari) models exist; Kannada/Malayalam absent |
| PaddleOCR | multi_languages.en.md (2.x) | https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version2.x/ppocr/blog/multi_languages.en.md | Official docs (repo) | 2026-09-08 | version2.x (legacy) | Confirms Kannada/Malayalam absent even from legacy ~80-language table |
| PaddleOCR | PP-OCRv5.md | https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5.md | Official docs (repo) | 2026-09-08 | PP-OCRv5 | Headline language groups |
| PaddleOCR docs site | paddleocr.ai latest index | https://www.paddleocr.ai/latest/en/index.html | Official docs site | 2026-09-08 | 3.x | Pipeline list (PP-OCRv5/v6, PP-StructureV3, PaddleOCR-VL, PP-ChatOCRv4) |
| PaddleX (official inference framework) | PP-StructureV3 pipeline usage | https://paddlepaddle.github.io/PaddleX/3.3/en/pipeline_usage/tutorials/ocr_pipelines/PP-StructureV3.html | Official docs | 2026-09-08 | PaddleX 3.3 | Layout/table/formula/reading-order capability, JSON bbox fields, Python usage |
| PaddleOCR-VL | Hugging Face model card | https://huggingface.co/PaddlePaddle/PaddleOCR-VL | Official model card | 2026-09-08 | PaddleOCR-VL-1.6 | Confirms real model, 109 languages, Apache 2.0, local execution via transformers/vLLM |
| docTR | Official GitHub repo | https://github.com/mindee/doctr | Official GitHub repo | 2026-09-08 | current main | Detection+recognition, bbox/confidence, direct PDF input, Apache 2.0; no Indic language mention |
| EasyOCR | Official GitHub repo | https://github.com/JaidedAI/EasyOCR | Official GitHub repo | 2026-09-08 | v1.7.2 (2024-09-24) | Apache 2.0, bbox+confidence output, image-only input (no direct PDF) |
| EasyOCR | Official language list (jaided.ai) | https://www.jaided.ai/easyocr/ | Official docs site | 2026-09-08 | current | Confirms te/hi/ta/kn supported, Malayalam absent |
