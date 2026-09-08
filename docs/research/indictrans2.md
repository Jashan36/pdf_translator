# Research: IndicTrans2 (AI4Bharat)

Date checked: 2026-09-08
Scope: E. IndicTrans2 — supported languages/codes, model variants, inference
pipeline, placeholder/protected-token handling, input length limits,
batching, CPU/GPU support, quantization, CTranslate2, license, benchmarks,
documented weaknesses.

Source priority followed per `technical-research` skill: official GitHub
repo (README, code) > official HF model cards > official paper (arXiv
2305.16307) > issue tracker > secondary/community sources (marked
explicitly where used).

## 1. Supported languages and exact codes

**Source:** https://github.com/AI4Bharat/IndicTrans2 (README, main branch),
fetched 2026-09-08.

IndicTrans2 supports all 22 scheduled languages of the Indian constitution,
using FLORES-200-style `xxx_Scrp` codes. Full verified list:

| Language | Code | Script |
|---|---|---|
| Assamese | `asm_Beng` | Bengali |
| Bengali | `ben_Beng` | Bengali |
| Bodo | `brx_Deva` | Devanagari |
| Dogri | `doi_Deva` | Devanagari |
| English | `eng_Latn` | Latin |
| Konkani (Goan) | `gom_Deva` | Devanagari |
| Gujarati | `guj_Gujr` | Gujarati |
| Hindi | `hin_Deva` | Devanagari |
| Kannada | `kan_Knda` | Kannada |
| Kashmiri (Arabic) | `kas_Arab` | Arabic |
| Kashmiri (Devanagari) | `kas_Deva` | Devanagari |
| Maithili | `mai_Deva` | Devanagari |
| Malayalam | `mal_Mlym` | Malayalam |
| Manipuri (Bengali) | `mni_Beng` | Bengali |
| Manipuri (Meitei) | `mni_Mtei` | Meitei Mayek |
| Marathi | `mar_Deva` | Devanagari |
| Nepali | `npi_Deva` | Devanagari |
| Odia | `ory_Orya` | Odia |
| Punjabi | `pan_Guru` | Gurmukhi |
| Sanskrit | `san_Deva` | Devanagari |
| Santali | `sat_Olck` | Ol Chiki |
| Sindhi (Arabic) | `snd_Arab` | Arabic |
| Sindhi (Devanagari) | `snd_Deva` | Devanagari |
| Tamil | `tam_Taml` | Tamil |
| Telugu | `tel_Telu` | Telugu |
| Urdu | `urd_Arab` | Arabic |

### Verified codes for this project's target languages

| Language | Code | Status |
|---|---|---|
| English | `eng_Latn` | Verified — AI4Bharat/IndicTrans2 README |
| Hindi | `hin_Deva` | Verified — AI4Bharat/IndicTrans2 README |
| Telugu | `tel_Telu` | Verified — AI4Bharat/IndicTrans2 README |
| Tamil | `tam_Taml` | Verified — AI4Bharat/IndicTrans2 README |
| Kannada | `kan_Knda` | Verified — AI4Bharat/IndicTrans2 README |
| Malayalam | `mal_Mlym` | Verified — AI4Bharat/IndicTrans2 README |

All 5 target languages (Telugu, Hindi, Tamil, Kannada, Malayalam) are
officially supported by IndicTrans2. Note: some script variants for other
languages (Kashmiri Devanagari, Manipuri Bengali, Sindhi Arabic) are
documented as "not directly supported due to lack of training data" per a
secondary summary (emergentmind.com) of the IndicTrans2-M2M follow-on work —
this does not affect Hindi/Telugu/Tamil/Kannada/Malayalam, which are
mainline, well-resourced languages in the project.

## 2. Model variants and where to get them

**Source:** https://github.com/AI4Bharat/IndicTrans2 README, and HF model
cards (huggingface.co/ai4bharat/...), fetched 2026-09-08.

Three translation directions, each with a base and a distilled variant:

| Direction | Variant | Params | HF repo |
|---|---|---|---|
| En→Indic | Base | ~1B | `ai4bharat/indictrans2-en-indic-1B` |
| En→Indic | Distilled | ~200M | `ai4bharat/indictrans2-en-indic-dist-200M` |
| Indic→En | Base | ~1B | `ai4bharat/indictrans2-indic-en-1B` |
| Indic→En | Distilled | ~200M | `ai4bharat/indictrans2-indic-en-dist-200M` |
| Indic→Indic | Base | ~1B | `ai4bharat/indictrans2-indic-indic-1B` |
| Indic→Indic | Distilled | ~320M | `ai4bharat/indictrans2-indic-indic-dist-320M` |

For this project's use case (English → Telugu/Hindi/Tamil/Kannada/
Malayalam), the relevant models are the **En-Indic base (1B)** or
**En-Indic distilled (200M)**.

Additionally, per the README's January 2025 update, AI4Bharat released
**"Long Context Models"** — RoPE-based variants supporting sequence lengths
up to 2048 tokens, distributed via a HuggingFace collection. One such
variant was found under `prajdabre/rotary-indictrans2-en-indic-1B` — note
this is hosted under an individual contributor's HF namespace
(`prajdabre`), not the `ai4bharat` org, so treat its "officialness" as
slightly lower confidence than the mainline `ai4bharat/*` repos even though
it is linked from the official README's changelog. Verify this
organizationally before depending on it.

## 3. Documented inference pipeline

**Source:** https://github.com/AI4Bharat/IndicTrans2 README and
`huggingface_interface/example.py` (fetched via GitHub, 2026-09-08); HF
model card for `ai4bharat/indictrans2-en-indic-1B`.

Two documented inference paths:

1. **Fairseq Python interface** (`inference/engine.py`):
   ```python
   from inference.engine import Model
   model = Model(ckpt_dir, model_type="fairseq")
   model.batch_translate(sentences, src_lang, tgt_lang)
   model.translate_paragraph(text, src_lang, tgt_lang)
   ```
   `translate_paragraph` exists as a distinct method from
   `batch_translate`, implying the engine does its own sentence splitting
   internally for paragraph-level input, but the README text fetched did
   not expose the exact splitting implementation/library — **this specific
   detail (which sentence splitter is used internally) is unverified from
   the README alone** and would need direct inspection of
   `inference/engine.py` source to confirm.

2. **HuggingFace `transformers` interface** (`huggingface_interface/`),
   used together with the **IndicTransToolkit** package (see companion doc
   `docs/research/indictrans-toolkit.md`). Official example
   (`huggingface_interface/example.py`):
   ```python
   from IndicTransToolkit import IndicProcessor
   from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

   ip = IndicProcessor(inference=True)
   tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indictrans2-en-indic-dist-200M")
   model = AutoModelForSeq2SeqLM.from_pretrained("ai4bharat/indictrans2-en-indic-dist-200M")

   batch = ip.preprocess_batch(input_sentences, src_lang=src_lang, tgt_lang=tgt_lang)
   inputs = tokenizer(batch, truncation=True, padding=True, return_tensors="pt")
   generated_tokens = model.generate(**inputs, num_beams=5, min_length=0, max_length=256)
   translations = ip.postprocess_batch(generated_tokens, lang=tgt_lang)
   ```
   Batch size in the official example is `BATCH_SIZE = 4`
   (`huggingface_interface/example.py`), processed via
   `range(0, len(input_sentences), BATCH_SIZE)` — this is example
   convenience code, not a hard model limit.

### Placeholder / protected-token handling (critical for this project)

**Source:** `huggingface_interface/example.py` (AI4Bharat/IndicTrans2,
official) plus the IndicTransToolkit `processor.py` behavior, corroborated
via WebSearch summary of the toolkit's changelog/docs, fetched 2026-09-08.

- The official example explicitly routes every translation call through
  `IndicProcessor.preprocess_batch()` before tokenization and
  `IndicProcessor.postprocess_batch()` after generation.
- `preprocess_batch()` is documented (per the toolkit's own
  changelog/description, corroborated by a secondary summary — see caveat
  below) to return a tuple of the preprocessed sentences **and a list of
  dictionaries mapping placeholders to their original values** — i.e. it
  performs its own entity/number/URL-style placeholder substitution before
  the sentence is fed to the model, and `postprocess_batch()` restores the
  original entities into the generated output ("entity replacement" per
  the `ai4bharat/indictrans2-en-indic-1B` model card).
- **Confidence caveat:** the exact regex/entity types handled (numbers,
  URLs, email addresses, dates, etc.) could not be directly confirmed from
  the toolkit's `processor.py` source — GitHub raw-file fetches for that
  path returned 404 during this research pass (the toolkit's internals are
  now implemented in Cython, which may affect how the file is served/named
  in the repo). Treat "which specific token types `IndicProcessor` protects
  automatically" as **unverified in detail** — confirm by reading the
  actual installed package source (`site-packages/IndicTransToolkit/`)
  before relying on it to preserve this project's protected-content system
  (URLs/numbers/entities). Do not assume `IndicProcessor`'s built-in entity
  protection is a substitute for this project's own protected-token
  pipeline — verify empirically with test sentences containing URLs,
  numbers, and dates before trusting it in production.

## 4. Practical input length limits

**Source:** AI4Bharat/IndicTrans2 README (fetched 2026-09-08);
`huggingface_interface/example.py`.

- Official example generation call uses `max_length=256` (output token
  cap) — this is a generation parameter in example code, not a documented
  hard architectural ceiling for the base/distilled models.
- Mainline models are effectively **sentence-level** — the two-method split
  in `inference/engine.py` (`batch_translate` for sentences vs.
  `translate_paragraph` for paragraphs, which the paragraph method must
  internally sentence-split) supports this reading, though the exact
  internal splitting mechanism is unverified (see Section 3 caveat).
- Since **January 2025**, AI4Bharat has released separate **"Long Context
  Models"** using RoPE, explicitly documented as "capable of handling
  sequence lengths up to 2048 tokens" (README changelog entry, dated
  2025-01-18). This is a distinct model family from the mainline
  base/distilled checkpoints — using it for paragraph-level translation
  would need to be an explicit, separate integration decision, not assumed
  to be the default IndicTrans2 behavior.
- **Recommendation for this project:** treat mainline IndicTrans2 as
  sentence-level unless/until the long-context variant is separately
  verified and adopted; feed it pre-segmented sentences produced by this
  project's own document model / sentence splitter rather than raw
  paragraph text.

## 5. Batching support

**Source:** AI4Bharat/IndicTrans2 README + `huggingface_interface/example.py`.

- Batch translation is a first-class, documented API:
  `model.batch_translate(sentences, src_lang, tgt_lang)` (fairseq
  interface), and manual batching (`BATCH_SIZE = 4` loop) in the HF
  example.
- The bash interface also exposes batch translation via
  `joint_translate.sh`.

## 6. CPU vs GPU inference; memory requirements

**Source:** AI4Bharat/IndicTrans2 README (fetched 2026-09-08) — **not
explicitly documented** by AI4Bharat. Secondary corroboration: a summary of
IndicTrans2-M2M follow-on material (emergentmind.com, tier 6/community,
2026-09-08) states the 1B models have "high GPU memory requirements" and
are "slow to use" on constrained hardware, with distilled variants cutting
decode time roughly in half in their reported test (~52s → ~33s on a
fixed test set, hardware unspecified in that source).

- **No official AI4Bharat CPU/GPU memory specification was found** in the
  README, model cards, or paper abstract during this research pass. This
  must be marked **unverified/undocumented** rather than assumed.
- Both HF (`transformers`) and CTranslate2 interfaces are standard
  PyTorch/CT2 stacks that run on CPU by default if no CUDA device is
  requested — this is a property of the underlying frameworks, not an
  AI4Bharat-specific guarantee, and inference speed on CPU is not
  benchmarked by AI4Bharat in the sources checked.
- **Practical implication:** for "family local machine" CPU-only use, the
  **distilled models (200M / 320M)** are the responsible choice over the
  1B base models, given the (secondary-sourced) size/speed relationship
  above — but actual CPU throughput/latency numbers should be benchmarked
  directly on the target machine before committing to a UX design (e.g.
  progress bar expectations), since AI4Bharat does not publish CPU
  latency figures.

## 7. Quantization support

**Source:** AI4Bharat/IndicTrans2 README, GitHub issue search (fetched
2026-09-08) — **not officially documented by AI4Bharat** as a first-class
feature of IndicTrans2 itself. No README section, issue, or model card
content found describing AI4Bharat-provided int8/fp16 quantized
checkpoints or an official quantization recipe.
- Quantization is available only indirectly, as a generic capability of
  **CTranslate2** (see Section 8) once a checkpoint is converted to CT2
  format — CTranslate2 itself documents int8/fp16 quantization options
  (OpenNMT/CTranslate2 project docs), but that is CTranslate2's own
  documented feature, not something AI4Bharat specifically validates or
  publishes accuracy numbers for on IndicTrans2 checkpoints.
- **Verdict: unverified/undocumented by AI4Bharat.** If quantization is
  needed for CPU performance, treat it as a community-pattern
  (CT2 int8) to validate independently (quality regression testing)
  before shipping, not an AI4Bharat-endorsed configuration.

## 8. CTranslate2 conversion — official or community?

**Source:** AI4Bharat/IndicTrans2 README, fetched 2026-09-08.

**Officially documented by AI4Bharat**, not merely community-discovered:
- The README explicitly provides CT2-ported model variants and describes
  using the CTranslate2 interface via the same `Model` class with
  `model_type="ctranslate2"`.
- The README also references the external `fairseq-ct2-converter` guide
  (https://opennmt.net/CTranslate2/guides/fairseq.html) for converting
  fine-tuned/custom checkpoints to CT2 format.
- This means CT2 is a supported, first-party inference path for IndicTrans2
  — a reasonable option to evaluate for CPU inference performance in this
  project, though (per Section 7) AI4Bharat does not itself publish
  quantized-CT2 benchmark numbers.

## 9. License

**Source:** AI4Bharat/IndicTrans2 README, fetched 2026-09-08.

- **Model checkpoints: MIT License** (a permissive license, compatible
  with a local-first commercial/personal tool).
- Training-data artifacts carry different licenses depending on origin
  (not relevant to using the released model checkpoints, but relevant if
  this project ever redistributes training data):
  - Mined/back-translation corpora (NLLB, Samanantar, Samanantar++,
    Comparable): CC0
  - Human-annotated seed corpora (BPCC-H-Wiki, BPCC-H-Daily): CC-BY-4.0
  - IN22 evaluation test sets: CC-BY-4.0

For this project (using released model checkpoints for local inference,
not redistributing AI4Bharat's training corpora), the operative license is
**MIT** on the model weights — no restriction found that would block local,
even commercial, use.

## 10. Official benchmarks and per-language quality differences

**Source:** AI4Bharat/IndicTrans2 README (benchmark section, fetched
2026-09-08); paper abstract page (arxiv.org/abs/2305.16307, fetched
2026-09-08); PDF full text (arxiv.org/pdf/2305.16307) — **could not be
rendered to text in this environment** (no `pdftoppm`/poppler available,
and `ar5iv` HTML mirror failed to convert this paper). Per-language
numeric score tables from the primary paper are therefore **not directly
verified** in this pass. What follows is corroborated through a secondary
aggregator (emergentmind.com) that directly quotes/cites the primary paper
(Gala et al., 2023 / arXiv:2305.16307) and a related paper (Das et al.,
2023, arXiv:2306.12693) — **treat as secondary-sourced, lower confidence
than a direct primary-source read, and re-verify from the PDF/HTML paper
directly before quoting specific numbers in any user-facing claim.**

Findings (with this caveat):
- Evaluation is done on the **IN22 benchmark** (IN22-Gen: 1,024 sentences
  combining Wiki+Web domains; IN22-Conv: 1,503 conversational sentences)
  and **FLORES-200** devtest, using **chrF++ as the primary metric**, with
  BLEU and COMET also reported and statistical significance testing
  applied (AI4Bharat/IndicTrans2 README — this part is primary-sourced).
- Per the secondary summary of the paper: on IN22-Gen and FLORES-200,
  IndicTrans2 exceeds open and commercial MT baselines "by 4–8 BLEU/chrF++
  in EN→Indic and 1–5 in Indic→EN" — an aggregate claim, not broken out
  per target language in the source checked.
- **Yes — per-language/per-family quality differences are documented,
  not uniform:** the paper is reported (secondary source, citing Das et
  al. 2023 which builds on the same benchmark family) to state that
  **"WI [Western Indo-Aryan: Hindi, Punjabi, Gujarati, Marathi]
  languages systematically outperform EI [Eastern Indo-Aryan] and
  Dravidian groups due to larger training data"** — meaning **Hindi
  (Indo-Aryan, high-resource) is expected to have measurably better
  translation quality than Telugu, Tamil, and Kannada (all Dravidian,
  comparatively lower-resource in this framing)**. This directly matters
  for setting per-language quality expectations/QA thresholds in this
  project — Hindi output should not be assumed to represent the quality
  level of Telugu/Tamil/Kannada output.
- Also reported: transliteration/tokenization artifacts specifically
  affecting **Malayalam and Tamil** ("exceptions in Malayalam and Tamil
  due to tokenization artifacts") — relevant since both are target
  languages for this project.
- **Action item:** before finalizing per-language QA thresholds, re-fetch
  and read the actual results tables in arXiv:2305.16307 (Table with
  per-language IN22-Gen/FLORES chrF++ scores) directly — this pass was
  blocked by local PDF-rendering tooling, not by source unavailability.

## 11. Known weaknesses / risks (AI4Bharat-documented or corroborated)

1. **Non-uniform language quality (documented):** Hindi/Indo-Aryan
   languages outperform Dravidian languages (Telugu, Tamil, Kannada) per
   the paper's own reported findings (Section 10) — do not assume uniform
   output quality across the project's 4 priority languages.
2. **Tokenization artifacts in Malayalam and Tamil (documented,
   secondary-sourced):** specifically called out as exceptions where
   transliteration/tokenization causes issues — both are target languages
   here; budget extra QA attention for these two.
3. **Large base model resource cost (partially documented,
   partially secondary-sourced):** 1B-parameter base models are
   description as requiring GPU / being slow on constrained hardware;
   AI4Bharat itself does not publish CPU numbers, so this is an inference,
   not a documented AI4Bharat claim — verify directly.
4. **No first-party CPU/GPU hardware requirement spec.** AI4Bharat has not
   published minimum RAM/VRAM figures for the released checkpoints in the
   README/model cards checked.
5. **No first-party quantization guidance.** Any quantization (int8, etc.)
   is via generic CTranslate2 features, not AI4Bharat-validated for
   translation-quality regression.
6. **Placeholder/entity-protection behavior of `IndicProcessor` is not
   fully documented at the token-type level** in the sources reachable
   here (Section 3) — must be empirically verified with real inputs
   (URLs, numbers, dates) before this project relies on it, or before
   deciding to bypass it and do protection entirely in this project's own
   pipeline (which CLAUDE.md's "protected-content" architecture would
   suggest is safer regardless).
7. **Partial script/language coverage gaps unrelated to this project's
   scope:** some script variants (Kashmiri Devanagari, Manipuri Bengali,
   Sindhi Arabic) are noted as unsupported in a follow-on model due to
   lack of training data — does not affect Telugu/Hindi/Tamil/
   Kannada/Malayalam but is evidence AI4Bharat is transparent about
   per-language coverage gaps.
8. **Long-context (2048-token) variant is separate from mainline
   checkpoints and one instance found is hosted outside the official
   `ai4bharat` HF org** (`prajdabre/...`) — verify org/official status
   before depending on it for paragraph-level translation.
9. **Could not verify primary-source benchmark tables directly** in this
   pass (PDF rendering tooling unavailable) — the per-language quality
   claims in Section 10 rest on a secondary aggregator, not a direct read
   of the paper's tables. Flagged for re-verification.

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| IndicTrans2 | AI4Bharat/IndicTrans2 GitHub README | https://github.com/AI4Bharat/IndicTrans2 | Official GitHub repo | 2026-09-08 | main branch (README last updated per repo, Jan 2025 changelog entry seen) | Full 22-language code list, model variants, license, CT2 support, benchmark methodology |
| IndicTrans2 | Raw README.md | https://raw.githubusercontent.com/AI4Bharat/IndicTrans2/main/README.md | Official GitHub repo (raw) | 2026-09-08 | main branch | Confirms IndicTransToolkit migration link, license breakdown, CT2/fairseq-ct2-converter reference |
| IndicTrans2 | huggingface_interface directory | https://github.com/AI4Bharat/IndicTrans2/tree/main/huggingface_interface | Official GitHub repo | 2026-09-08 | main branch | HF usage entry point, links to IndicTransToolkit |
| IndicTrans2 | huggingface_interface/example.py | https://github.com/AI4Bharat/IndicTrans2/blob/main/huggingface_interface/example.py | Official GitHub repo (source file) | 2026-09-08 | main branch | Official inference example: preprocess_batch/postprocess_batch usage, BATCH_SIZE=4, max_length=256, num_beams=5 |
| IndicTrans2 | Model card: ai4bharat/indictrans2-en-indic-1B | https://huggingface.co/ai4bharat/indictrans2-en-indic-1B | Official HF model card | 2026-09-08 | 1B base, En-Indic | License (MIT), example usage via IndicProcessor, "entity replacement" in postprocessing |
| IndicTrans2 | Model card: ai4bharat/indictrans2-indic-en-1B | https://huggingface.co/ai4bharat/indictrans2-indic-en-1B | Official HF model card | 2026-09-08 | 1B base, Indic-En | Confirms repo naming pattern |
| IndicTrans2 | Paper abstract page | https://arxiv.org/abs/2305.16307 | Official paper (arXiv) | 2026-09-08 | arXiv:2305.16307 | Abstract: BPCC corpus, IN22 benchmark, "first model to support all 22 languages" |
| IndicTrans2 | Paper PDF | https://arxiv.org/pdf/2305.16307 | Official paper (arXiv, PDF) | 2026-09-08 | arXiv:2305.16307 | Could not render locally (no poppler); per-language score tables NOT directly verified |
| IndicTrans2 (secondary) | IndicTrans2: Multilingual Neural MT for Indian Languages | https://www.emergentmind.com/topics/indictrans2 | Secondary aggregator, citing primary papers | 2026-09-08 | n/a | Per-language/family quality gap (WI vs Dravidian), Malayalam/Tamil tokenization artifact claims — **re-verify against primary PDF** |
| IndicTrans2-M2M (secondary) | AI4Bharat blog, IndicTrans2-M2M | https://ai4bharat.iitm.ac.in/blog/indictrans2/ | Official AI4Bharat blog | 2026-09-08 | n/a | 1B model "slow"/"high GPU memory" claim (informal, not a spec); unsupported script variants in M2M follow-on |
| IndicTransToolkit | GitHub repo (VarunGumma) | https://github.com/VarunGumma/IndicTransToolkit | Community repo, linked from official IndicTrans2 README | 2026-09-08 | see companion doc | Not built/tested for Windows; IndicProcessor API |

See `docs/research/indictrans-toolkit.md` for the toolkit-specific source
table and findings.
