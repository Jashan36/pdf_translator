# Document Parsing / Structure Engines Research — Docling vs PP-Structure vs PyMuPDF baseline

Date checked: 2026-09-08
Scope: master plan Section 16 (Docling) and Section 49 (Phase 8 —
Tables and Complex Layout). This project's need is **reversible,
layout-preserving localization** — reconstructing a translated PDF
that visually matches the original — NOT document-to-Markdown
conversion. Every claim below is sourced from a live fetch of an
official source on 2026-09-08; anything not confirmed is marked
UNVERIFIED.

## 1. Docling — what it actually provides

Official repo: https://github.com/docling-project/docling
Official docs: https://docling-project.github.io/docling/

- **Text extraction**: parses PDF, DOCX, PPTX, XLSX, HTML, images,
  and more into a unified representation.
- **Layout detection**: "Advanced PDF understanding incl. page layout,
  reading order, table structure, code, formulas, image
  classification, and more." Source:
  https://docling-project.github.io/docling/
- **Reading order**: explicitly restores logical reading order as
  part of the same pipeline (used e.g. for correct Markdown export
  order).
- **Tables**: dedicated **TableFormer** model for table structure
  recognition, confirmed on the official docs page.
- **OCR integration**: "extensive OCR support for scanned PDFs and
  images" — the usage docs show worked examples wiring in Tesseract
  (with automatic language detection), RapidOCR, and SuryaOCR as
  pluggable OCR backends. Source:
  https://docling-project.github.io/docling/usage/
- **Coordinate/bbox output fidelity**: the **DoclingDocument** data
  model explicitly carries "Layout information (i.e. bounding boxes)
  for all items, if available" plus provenance information tying each
  content item back to a page. This means bounding-box-level geometry
  survives into Docling's own JSON representation — not just prose.
  Source: https://docling-project.github.io/docling/concepts/docling_document/
  (NOTE: the exact field names — expected to be something like `prov`
  / `bbox` / `PageItem` based on the described behavior — could **not**
  be confirmed verbatim from the fetched page content; the tool
  summarizing the page did not quote the schema literally. Treat the
  *existence* of per-item bbox+page provenance as confirmed, but the
  *exact field names* as UNVERIFIED until the `docling-core` schema or
  API reference is read directly at implementation time.)
- **Local execution**: docs explicitly market "local execution
  capabilities for sensitive data and air-gapped environments" — this
  matches this project's local-first/privacy requirement (CLAUDE.md
  Privacy rule).
- **License**: MIT. Confirmed by fetching the repo LICENSE file.
  Source: https://github.com/docling-project/docling/blob/main/LICENSE
- **Python compatibility**: Python 3.10+ (3.9 support was dropped in
  Docling v2.70.0, per the repo).
- **Indic language / OCR language support**: **UNVERIFIED as a Docling
  feature.** Docling itself does not run its own OCR text-recognition
  model — it delegates to whichever OCR backend is plugged in
  (Tesseract, RapidOCR, SuryaOCR, EasyOCR are all mentioned as
  integrable backends in various parts of the docs). This means
  Telugu/Hindi/Tamil/Kannada/Malayalam OCR support, if ever needed
  through Docling, would be inherited from whatever OCR engine is
  configured underneath it — the same language-coverage gaps found in
  `docs/research/ocr.md` (e.g. Kannada/Malayalam gaps) would apply.
  Docling's own docs page did not enumerate OCR-backend language
  coverage; that would need checking against the specific chosen OCR
  backend, not against Docling itself.

## 2. PP-Structure (PaddleOCR's structure pipeline) — current status

Per `docs/research/ocr.md` Section 3 (also verified there against the
official PaddleX pipeline docs), the current, actively maintained
structure pipeline in the PaddleOCR 3.x family is **PP-StructureV3**
(the "PP-Structure" name from the master plan is the still-correct
family name; the specific current version is V3). It provides:

- Layout detection, reading-order restoration, table recognition
  (HTML/XLSX export), formula recognition, and underlying OCR — in one
  pipeline, using the PaddleX inference framework.
  Source: https://paddlepaddle.github.io/PaddleX/3.3/en/pipeline_usage/tutorials/ocr_pipelines/PP-StructureV3.html
- **Coordinate/bbox output fidelity**: JSON output includes
  `block_bbox` (per-layout-region box), `dt_polys`/`rec_polys`
  (per-text-line polygons), and explicit `block_id`/`block_order`
  reading-order indices — comparable in kind to Docling's provenance
  data, and arguably more concretely documented (exact field names
  were directly confirmed here, unlike Docling's schema).
- **Local execution**: yes — it's a Python package (`paddlex`/
  `paddleocr`) that runs locally; same local-first fit as Docling.
- **License**: Apache 2.0 (whole PaddleOCR project, confirmed via
  LICENSE file — see `docs/research/ocr.md`).
- Being part of the PaddleOCR family, it **only makes sense to adopt
  alongside OCR itself** (Phase 7+), since its primary value-add over
  plain PyMuPDF is precisely the OCR-driven table/layout/reading-order
  analysis for scanned or image-based content. For native-text PDFs,
  PyMuPDF already has the real text/geometry and doesn't need a
  structure-inference model to guess it.

## 3. PyMuPDF (baseline, for comparison only — not re-researched here)

Per the parallel agent's baseline research (not re-verified in this
pass — noted here only for comparison context): PyMuPDF reads native
PDF structure directly (text objects, exact coordinates, fonts) with
no inference involved, which is the highest-fidelity path for
native-text PDFs and the foundation this whole project's rendering
strategy is built on (CLAUDE.md Core principle: "Never ask an LLM to
guess PDF geometry... that is PyMuPDF's job").

## 4. Comparison table

| Criterion | PyMuPDF (baseline) | Docling | PP-StructureV3 |
|---|---|---|---|
| Real bounding boxes for reconstruction | Yes — exact, from native PDF objects, no inference | Yes — DoclingDocument carries per-item bbox + page provenance (schema field names UNVERIFIED verbatim) | Yes — explicit `block_bbox`, `dt_polys`/`rec_polys`, confirmed field names |
| Primary output orientation | Structured geometry (blocks/lines/spans/chars) | Markdown/JSON/HTML — markets itself around Markdown/RAG use cases, but JSON path retains geometry | JSON/Markdown/HTML/XLSX — geometry retained in JSON path |
| Table structure fidelity | Basic (no dedicated table model — geometry only, no semantic table understanding) | Dedicated TableFormer model — explicit table-structure recognition | Dedicated table recognition — HTML/XLSX export of table structure |
| Reading order | Not needed for native reconstruction (renders at original coordinates); no reading-order inference | Explicit reading-order restoration | Explicit reading-order restoration (`block_order`) |
| OCR integration | None (not an OCR tool) | Pluggable (Tesseract/RapidOCR/SuryaOCR/others) — Docling does not do its own recognition | Native, built-in (PP-OCRv5/v6 under the hood) |
| Meant for local execution | Yes | Yes (explicitly marketed for air-gapped/local use) | Yes |
| License | AGPL/commercial dual-license for PyMuPDF itself — **not re-verified in this pass**, see baseline agent's findings | MIT (confirmed) | Apache 2.0 (confirmed) |
| Best fit in this project | Primary path for all native-text PDFs (current milestone) | Optional structural analyzer for genuinely complex documents (multi-column, dense tables) once basic pipeline is proven | Only relevant once OCR/scanned-PDF support (Phase 7+) is built, as the table/layout half of that same effort |

Note on PyMuPDF license: this file does not re-verify PyMuPDF's
license since the master plan says a parallel agent already covered
PyMuPDF as the baseline — that claim should be cross-checked against
that agent's own sourced output, not assumed here.

## 5. Recommendation: should Docling be used, and how?

**Recommendation: use Docling as an optional structural analyzer for
complex documents only — exactly as master plan Section 16 and Section
49 already specify. Do not make it the primary parser, and do not
adopt it now.**

Justification from evidence gathered:

1. **It doesn't need to be the primary parser** because PyMuPDF
   already extracts exact native-PDF geometry with zero inference
   error for the current milestone (native-text PDFs) — Docling's
   layout/table/reading-order *inference* is solving a problem
   PyMuPDF's native-text path doesn't have. Inference is only valuable
   where structure is ambiguous (dense multi-column layouts, merged
   cells, scanned pages) — i.e. "complex documents," matching the
   master plan's own framing.
2. **It is not disqualified by license or execution model** — MIT
   license (permissive, compatible) and explicit local-execution
   support both check out, so there's no blocking reason it couldn't
   be added later.
3. **It does preserve bounding boxes**, per its own docs
   (`docling_document` concept page), so it would not silently
   degrade this project's reversible-layout requirement the way a
   pure Markdown-out tool would — but the *exact* schema needs
   confirming from `docling-core` source/API reference before code is
   written against it (flagged as UNVERIFIED above); don't copy a
   schema from memory when that milestone arrives.
4. **Skipping it entirely would be premature** — for Phase 8's stated
   needs (merged cells, repeated headers, multi-column reading order,
   captions, footnotes), Docling is a purpose-built tool with a
   dedicated table-structure model (TableFormer) and reading-order
   restoration, which is more than PyMuPDF's raw block/line/span
   extraction offers on its own for genuinely hard layouts.
5. **PP-StructureV3 is a plausible substitute for the same job**, but
   it comes bundled with the PaddleOCR/PaddleX dependency stack and is
   most naturally introduced together with OCR (Phase 7), not before.
   If OCR is already in the stack by the time Phase 8 is reached,
   re-evaluate whether PP-StructureV3's built-in structure pipeline
   makes a separate Docling dependency redundant — but that's a
   Phase 7/8-time decision, not now.

**Do not add Docling as a dependency for the current milestone.** Per
the master plan's own phase ordering and this project's "earn
complexity only when the previous layer is proven" rule, it belongs at
Phase 8 (Tables and Complex Layout), as an optional layer behind
PyMuPDF, exactly as Section 16's diagram shows:

```text
PDF → PyMuPDF → Docling for complex structure → Internal Document Model
→ Translation → Our rendering engine
```

## What could NOT be verified

- Exact DoclingDocument schema field names (`prov`, `bbox`, `PageItem`
  or equivalent) — the concept was confirmed, the literal field names
  were not quoted verbatim from the fetched page. Needs a direct read
  of `docling-core`'s data model or the API reference at
  implementation time.
- Whether Docling's OCR-backend integrations (Tesseract/RapidOCR/
  SuryaOCR) have been tested by the Docling project against Telugu/
  Hindi/Tamil/Kannada/Malayalam specifically — not addressed in the
  pages fetched. UNVERIFIED.
- PyMuPDF's exact license terms — intentionally not re-verified here
  per the task's instruction that a parallel agent already covers it
  as baseline; do not treat anything in this file as a PyMuPDF license
  determination.

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| Docling | Official GitHub repo | https://github.com/docling-project/docling | Official GitHub repo | 2026-09-08 | current main | Feature overview, MIT license reference, Python 3.10+ |
| Docling | LICENSE | https://github.com/docling-project/docling/blob/main/LICENSE | Official GitHub repo | 2026-09-08 | n/a | MIT license confirmed |
| Docling | Official docs homepage | https://docling-project.github.io/docling/ | Official docs site | 2026-09-08 | current | Layout/reading-order/table/OCR feature list, local execution claim |
| Docling | DoclingDocument concept page | https://docling-project.github.io/docling/concepts/docling_document/ | Official docs site | 2026-09-08 | current | Confirms per-item bbox + page provenance is part of the data model (exact field names unverified) |
| Docling | Usage / OCR engines page | https://docling-project.github.io/docling/usage/ | Official docs site | 2026-09-08 | current | Confirms pluggable OCR backends (Tesseract, RapidOCR, SuryaOCR); basic `DocumentConverter` usage example |
| PaddleX / PP-StructureV3 | Pipeline usage tutorial | https://paddlepaddle.github.io/PaddleX/3.3/en/pipeline_usage/tutorials/ocr_pipelines/PP-StructureV3.html | Official docs | 2026-09-08 | PaddleX 3.3 | Layout/table/formula/reading-order pipeline, JSON bbox field names, Python usage |
| PaddleOCR | LICENSE (covers PP-StructureV3) | https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE | Official GitHub repo | 2026-09-08 | n/a | Apache 2.0 confirmed |
