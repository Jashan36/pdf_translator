# Research Sources

Aggregated from all `docs/research/*.md` files. Each topic file also
carries its own local Sources table — this is the consolidated index.
All entries checked 2026-09-08 unless noted.

## PyMuPDF / PDF internals

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| PyMuPDF | PyPI project page | https://pypi.org/project/PyMuPDF/ | Official package index | 1.28.2 (2026-08-06) | Current version, AGPL/commercial dual license, Python >=3.10 |
| PyMuPDF | GitHub Releases | https://github.com/pymupdf/PyMuPDF/releases | Official repo | 1.28.2 | Built on MuPDF 1.28.0 |
| PyMuPDF | TextPage docs | https://pymupdf.readthedocs.io/en/latest/textpage.html | Official docs | latest | get_text() modes; font-flags unreliability warning |
| PyMuPDF | Appendix 1 | https://pymupdf.readthedocs.io/en/latest/app1.html | Official docs | latest | block/line/span/char dict structure |
| PyMuPDF | Page class docs | https://pymupdf.readthedocs.io/en/latest/page.html | Official docs | latest | apply_redactions, add_redact_annot, insert_text/textbox/htmlbox, get_images/get_image_rects/get_drawings/get_pixmap |
| PyMuPDF | Document class docs | https://pymupdf.readthedocs.io/en/latest/document.html | Official docs | latest | extract_image, xref_* low-level API |
| PyMuPDF | functions.html | https://pymupdf.readthedocs.io/en/latest/functions.html | Official docs | latest | get_text_length, Base-14/CJK-only limit |
| PyMuPDF | Font class docs | https://pymupdf.readthedocs.io/en/latest/font.html | Official docs | latest | Font.text_length works for any font incl. custom |
| PyMuPDF | FAQ | https://pymupdf.readthedocs.io/en/latest/faq/index.html | Official docs | latest | redact+reinsert pattern; sort=True caveat |
| PyMuPDF | GitHub Discussion #3422 | https://github.com/pymupdf/PyMuPDF/discussions/3422 | Official discussion | n/a | Community-confirmed text-replacement pattern |
| PyMuPDF | GitHub Issue #530 | https://github.com/pymupdf/PyMuPDF/issues/530 | Official issue tracker | n/a | ToUnicode extraction failure mode |
| PDF format | ISO 32000-2:2020 listing | https://www.iso.org/obp/ui/#iso:std:iso:32000:-2:ed-1:v1:en | Official standards body | ISO 32000-2:2020 | Confirms current spec identity |
| PDF format | PDF Association resource page | https://pdfa.org/resource/iso-32000-2/ | Official standards org | ISO 32000-2:2020 | Free spec download (403'd during research) |
| PDF format | Adobe PDF32000_2008.pdf | https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf | Official spec | PDF32000_2008 | Too large to fetch in this pass |
| PDF format | Wikipedia: PDF | https://en.wikipedia.org/wiki/PDF | Secondary | n/a | Content streams, fonts, XObjects, transparency, OCG |
| PDF format | W3C WCAG PDF3 technique | https://www.w3.org/TR/WCAG20-TECHS/PDF3.html | Official W3C | WCAG 2.0 | Structure tree drives reading order, not content order |
| PDF format | Adobe SDK PDOCG reference | https://opensource.adobe.com/dc-acrobat-sdk-docs/pdflsdk/apireference/PD_Layer/PDOCG.html | Official Adobe SDK | n/a | OCG (layers) object model |

## OCR

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| PaddleOCR | GitHub repo / releases | https://github.com/PaddlePaddle/PaddleOCR | Official repo | v3.7.0 | Current major version 3.x; PP-OCRv5/v6, PaddleOCR-VL, PP-StructureV3 all confirmed real |
| PaddleOCR-VL | HF model card | (see ocr.md) | Official model card | current | Confirms PaddleOCR-VL is real and current |
| PaddleOCR | Official docs / PaddleX docs | (see ocr.md) | Official docs | current | New `.predict()` API replaces old `.ocr(img, cls=True)` |
| PaddleOCR | LICENSE | (see ocr.md) | Official repo | current | License terms |
| docTR | Official repo | https://github.com/mindee/doctr | Official repo | current | Apache-2.0, no Malayalam coverage found |
| EasyOCR | Official repo/docs | https://github.com/JaidedAI/EasyOCR | Official repo | current | Covers Kannada (gap in PaddleOCR); no Malayalam found |

*(Full 7-row tables with exact URLs are in `docs/research/ocr.md` and `docs/research/document-parsing.md` — condensed here for the index.)*

## Document parsing

| Technology | Title | Source type | Version/release | Relevant finding |
|---|---|---|---|---|
| Docling | Official repo + LICENSE + docs | Official repo | current | MIT license, local execution, DoclingDocument model w/ per-item bboxes (exact schema unverified) |
| PP-StructureV3 | PaddleOCR/PaddleX docs | Official docs | current | Bundled with PaddleOCR/PaddleX stack |

## IndicTrans2 / IndicTransToolkit

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| IndicTrans2 | AI4Bharat/IndicTrans2 README | https://github.com/AI4Bharat/IndicTrans2 | Official repo | current | Language codes, variants, license, CT2 support |
| IndicTrans2 | example.py | https://github.com/AI4Bharat/IndicTrans2 (huggingface_interface/example.py) | Official source | current | Pipeline/placeholder handling |
| IndicTrans2 | HF model card ai4bharat/indictrans2-en-indic-1B | https://huggingface.co/ai4bharat/indictrans2-en-indic-1B | Official model card | current | Usage, license |
| IndicTrans2 | Paper abstract | arXiv:2305.16307 | Official paper | current | Corpus/benchmark methodology |
| IndicTrans2 | Per-language quality gap | emergentmind.com (secondary, cites primary paper) | Secondary | n/a | Hindi/Indo-Aryan > Telugu/Tamil/Kannada/Dravidian quality gap — flagged for re-verification |
| IndicTrans2 | AI4Bharat blog (IndicTrans2-M2M) | Official blog | current | Informal GPU/speed remarks |
| IndicTransToolkit | VarunGumma/IndicTransToolkit | https://github.com/VarunGumma/IndicTransToolkit | Community repo, AI4Bharat-endorsed | 1.1.1 | Not an official AI4Bharat repo; explicitly not built/tested for Windows |
| IndicTransToolkit | PyPI JSON | https://pypi.org/pypi/IndicTransToolkit/json | Official index | 1.1.1 | MIT license, Python >=3.10 |
| IndicTransToolkit | AI4Bharat/IndicTransToolkit (404 check) | github.com/AI4Bharat/IndicTransToolkit | N/A — confirms non-existence | n/a | No official org repo exists |

## Translation architecture

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| Google Cloud Translation | Cloud Translation Advanced details | https://docs.cloud.google.com/translate/docs/intro-to-v3 | Official docs | current (v3 Advanced) | Translates whole paragraph at once; Adaptive Translation context windows |
| Google Cloud Translation | Translate documents | https://docs.cloud.google.com/translate/docs/advanced/translate-documents | Official docs | current | Preserves formatting/layout; PDF up to 20MB/300 pages |
| Document-level MT | Survey of context in NMT | Cambridge journal (peer-reviewed) | n/a | Sentence-independent NMT is the baseline context-methods fix |
| Document-level MT | Comparison of approaches to document-level MT | arXiv:2101.11040 | Preprint | n/a | ~1000-subword-token context gave strong gains over sentence-level |
| Document-level MT | Efficiently exploring LLMs for doc-level MT | arXiv:2406.07081 | Preprint | n/a | Bounded/partial document context via in-context learning |
| Document-level MT | Source-primed multi-turn conversation | arXiv:2503.10494 | Preprint | n/a | Priming once with doc context vs. resending per unit |
| NLLB | facebook/nllb-200-3.3B model card | https://huggingface.co/facebook/nllb-200-3.3B | Official model card | 3.3B | Disclaims production/document-translation use |

## Qwen3 / Ollama

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| Ollama | Qwen3 library page | https://ollama.com/library/qwen3 | Official (Ollama library) | qwen3 (current) | Sizes 0.6b–235b, default context 40K/256K by tag |
| Ollama | Qwen3 tags page | https://ollama.com/library/qwen3/tags | Official (Ollama library) | qwen3 (current) | Full exact tag list incl. quantizations, 2507 variants |
| Qwen (Alibaba) | Qwen3 official blog | https://qwenlm.github.io/blog/qwen3/ | Official blog | Qwen3 launch | 119 languages incl. Indic; Apache 2.0; native context 32K/128K |
| Qwen (Alibaba) | QwenLM/Qwen3 GitHub repo | https://github.com/QwenLM/Qwen3 | Official repo | Qwen3 (incl. 2507) | Apache 2.0 confirmed; 2507 refresh native 256K, extendable to 1M |
| Qwen (Alibaba) | Qwen/Qwen3-8B model card | https://huggingface.co/Qwen/Qwen3-8B | Official model card | Qwen3-8B | 32,768 native/131,072 via YaRN; no Indic-specific benchmark |
| Alibaba/Qwen | Official X/Twitter post | https://x.com/Alibaba_Qwen/status/1916962096346202468 | Official social | Qwen3 launch | "119 languages and dialects" |
| Ollama | API reference | https://github.com/ollama/ollama/blob/main/docs/api.md | Official docs | current | Streaming/non-streaming; format JSON/schema; tools |
| Ollama | Structured outputs | https://ollama.com/blog/structured-outputs | Official blog/docs | current | JSON-schema-constrained output |

## PDF typography / Indic shaping

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| PyMuPDF | Discussion #3568 | https://github.com/pymupdf/PyMuPDF/discussions/3568 | Official repo | post-1.23.8 | Devanagari cannot be written via insert_text/insert_textbox/TextWriter |
| PyMuPDF | Artifex blog: insert_htmlbox | artifex.com/blog/mastering-pdf-text-with-pymupdfs-insert-htmlbox-what-you-need-to-know | Official vendor blog | v1.23.8+ | insert_htmlbox uses HarfBuzz internally |
| PyMuPDF | Discussion #3659 | https://github.com/pymupdf/PyMuPDF/discussions/3659 | Official repo | current | insert_text has no fallback-font support |
| HarfBuzz | What is HarfBuzz? | harfbuzz.github.io/what-is-harfbuzz.html | Official docs | current | Selects/positions glyphs per Unicode text+font |
| HarfBuzz | What does HarfBuzz do? | harfbuzz.github.io/what-does-harfbuzz-do.html | Official docs | current | Shaping only, not rasterization; explicit Indic support |
| HarfBuzz | Shaping concepts | harfbuzz.github.io/shaping-concepts.html | Official docs | current | Defines "complex scripts" |
| Unicode Consortium | Unicode 16.0.0 Ch.12 | unicode.org/versions/Unicode16.0.0/core-spec/chapter-12/ | Official standard | 16.0.0 | Authoritative reordering/conjunct description |
| Noto Fonts | notofonts org repos | github.com/notofonts/{telugu,devanagari,tamil,kannada} | Official repo | current | Official, maintained repos exist |
| Noto Fonts | LICENSE | github.com/notofonts/noto-fonts/blob/main/LICENSE | Official repo | OFL v1.1 | Open, embeddable license |

## Layout fitting

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| PyMuPDF | Font class docs | pymupdf.readthedocs.io/en/latest/font.html | Official docs | current | Font.text_length() measurement API |
| PyMuPDF | Discussion #1915 | github.com/pymupdf/PyMuPDF/discussions/1915 | Official repo | current | Legacy vs current measurement API |
| PyMuPDF | Appendix 1 | pymupdf.readthedocs.io/en/latest/app1.html | Official docs | current | bbox extraction for collision detection |
| OpenType shaping | Indic shaping in OpenType | github.com/n8willis/opentype-shaping-documents | Community technical reference | current | 2D glyph placement complexity |

## Visual QA

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| scikit-image | structural_similarity API | scikit-image.org/docs/stable/api/skimage.metrics.html | Official docs | current stable | SSIM measures structure, tolerant of anti-aliasing |
| PyMuPDF | Images recipes | pymupdf.readthedocs.io/en/latest/recipes-images.html | Official docs | current | get_pixmap/save for rendering |
| pytesseract | Official repo | github.com/madmaze/pytesseract | Official repo | Apache 2.0, Py3.6+ | image_to_string API, multi-language support |

## Streamlit

| Technology | Title | URL | Source type | Version/release | Relevant finding |
|---|---|---|---|---|---|
| Streamlit | st.file_uploader | docs.streamlit.io/develop/api-reference/widgets/st.file_uploader | Official docs | current | 200MB default, config options |
| Streamlit | st.status | docs.streamlit.io/develop/api-reference/status/st.status | Official docs | current | Status container vs progress bar |
| Streamlit | st.download_button | docs.streamlit.io/develop/api-reference/widgets/st.download_button | Official docs | current | Callable data runs on separate thread |
| Streamlit | Session State | docs.streamlit.io/develop/concepts/architecture/session-state | Official docs | current | Persistence across reruns |
| Streamlit | Caching | docs.streamlit.io/develop/concepts/architecture/caching | Official docs | current | cache_data vs cache_resource; no async/threading guidance found |

## Notes on source quality

- All 5 research passes explicitly marked UNVERIFIED items rather than
  guessing (e.g. Docling's exact bbox schema, mixed-language-per-page
  OCR support, official CPU/RAM benchmarks for IndicTrans2). These are
  carried into `EXPERIMENTS.md` rather than treated as settled.
- The IndicTrans2 per-language quality-gap finding rests on a
  secondary source (emergentmind.com) citing the primary paper — the
  paper PDF itself could not be rendered locally in this pass. Treat
  as probable but re-verify against the primary paper before making it
  a hard product claim to users.
- Two PDF-spec sources (ISO 32000-2 full text, Adobe's PDF32000_2008.pdf)
  could not be fetched (403 / size limit) — PDF-internals claims about
  low-level operators rest on secondary sources (Wikipedia, W3C, Adobe
  SDK reference pages) rather than a direct spec quote. Acceptable for
  architectural decisions at this stage; revisit only if a byte-level
  spec question arises later.
