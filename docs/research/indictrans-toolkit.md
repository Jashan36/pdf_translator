# Research: IndicTransToolkit (AI4Bharat ecosystem)

Date checked: 2026-09-08
Scope: F. IndicTransToolkit — required/recommended/optional status, current
API, version/install, integration with IndicTrans2.

Source priority followed per `technical-research` skill: official
IndicTrans2 GitHub repo (as the authority on whether the toolkit is
required) > the toolkit's own GitHub repo/README > PyPI metadata >
secondary sources (marked explicitly).

## Important finding: "official AI4Bharat repo" framing needs a caveat

The task description asks to find "the official IndicTransToolkit
repository (also AI4Bharat)". This was checked directly:

- `https://github.com/AI4Bharat/IndicTransToolkit` returns **HTTP 404** —
  **there is no such repository under the AI4Bharat GitHub org.**
  (Checked 2026-09-08.)
- The actual repository is **`https://github.com/VarunGumma/IndicTransToolkit`**,
  maintained by an individual (Varun Gumma), **not** under the `AI4Bharat`
  GitHub organization.
- However, this is not a random third-party fork: the **official**
  `AI4Bharat/IndicTrans2` README explicitly states (as of a Dec 30, 2023
  changelog entry) that the IndicTrans2 HF tokenizer code was
  **"migrated to [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit)
  and is maintained separately there from now onwards"** — i.e. AI4Bharat's
  own official repo delegates/links to this community-maintained package as
  the canonical companion tool, and AI4Bharat's own official example code
  (`huggingface_interface/example.py`) imports and uses it.
- **Conclusion:** treat IndicTransToolkit as **AI4Bharat-endorsed and
  officially depended-upon**, but **not an AI4Bharat-org-owned repository**.
  This project's dependency records (`docs/dependencies.md`) should note
  the maintainer is a third party, even though usage is effectively
  mandated by AI4Bharat's own official example code (see Section 1 below).

## 1. Is it required, recommended, or optional for using IndicTrans2?

**Verdict: Required for the officially documented HuggingFace
`transformers` inference path; not applicable to the separate fairseq
(`inference/engine.py`) path.**

Evidence:
- AI4Bharat's own official README states the HF-compatible tokenizer code
  was moved out of the main `IndicTrans2` repo and **into**
  IndicTransToolkit — meaning the tokenizer/pre-post-processing logic
  needed to correctly use the `ai4bharat/indictrans2-*` HF checkpoints is
  no longer bundled in `IndicTrans2` itself.
  (Source: https://github.com/AI4Bharat/IndicTrans2, README, fetched
  2026-09-08.)
- AI4Bharat's official `huggingface_interface/example.py` — the canonical
  usage example for the HF models — directly imports and uses it:
  ```python
  from IndicTransToolkit import IndicProcessor
  ...
  ip = IndicProcessor(inference=True)
  batch = ip.preprocess_batch(input_sentences, src_lang=src_lang, tgt_lang=tgt_lang)
  ...
  translations = ip.postprocess_batch(generated_tokens, lang=tgt_lang)
  ```
  (Source: https://github.com/AI4Bharat/IndicTrans2/blob/main/huggingface_interface/example.py,
  fetched 2026-09-08.)
- The `ai4bharat/indictrans2-en-indic-1B` official HF model card's own
  usage snippet also goes through `IndicProcessor` for pre/post-processing
  and "entity replacement." (Fetched 2026-09-08.)
- The **fairseq** interface (`inference/engine.py`,
  `Model(ckpt_dir, model_type="fairseq")`) is a separate code path bundled
  directly in the `IndicTrans2` repo and does not appear (from the README)
  to require IndicTransToolkit — that path predates/parallels the HF
  migration.

**Practical implication for this project:** if this project integrates
IndicTrans2 via the HuggingFace `transformers` interface (the more common,
better-supported path for a Python application), **IndicTransToolkit is a
required dependency**, not optional — skipping it means reimplementing its
tokenizer pre/post-processing (including whatever entity/number protection
logic it performs — see the companion `indictrans2.md` Section 3 caveat)
from scratch, which is not officially documented step-by-step outside the
toolkit's own source.

## 2. Current API surface

**Source:** WebFetch of https://github.com/VarunGumma/IndicTransToolkit
(README) and WebSearch corroboration of `processor.py` behavior, fetched
2026-09-08. Direct raw-file fetch of `IndicTransToolkit/processor.py`
returned 404 in this pass (repo internals are now Cython-based per the
README, which may affect file layout/naming) — so exact regex/entity-type
details are **not independently confirmed from source** here; see caveat
below.

Documented public API (from README + corroborating search results):

- **`IndicProcessor`** class (now implemented in Cython for performance,
  per the README) — the main entry point.
  ```python
  from IndicTransToolkit import IndicProcessor
  # or: from IndicTransToolkit.processor import IndicProcessor
  ip = IndicProcessor(inference=True)
  ```
- **`ip.preprocess_batch(sentences, src_lang, tgt_lang, visualize=False)`**
  — takes raw sentences plus FLORES-style source/target language codes;
  performs normalization/tagging needed before tokenization. A
  corroborating secondary description (from search-result summaries of the
  package's own docs/changelog) states this method **"returns a tuple of a
  list of preprocessed input text sentences and a corresponding list of
  dictionaries mapping placeholders to their original values"** — i.e. it
  does entity/placeholder substitution and hands back the mapping needed
  to restore it later. The `visualize` keyword (tqdm progress bar) was
  reported as a newer addition per a changelog reference.
- **`ip.postprocess_batch(generated_tokens, lang)`** — restores
  entities/placeholders into the decoded model output ("entity
  replacement" per the official `ai4bharat/indictrans2-en-indic-1B` model
  card usage example).
- **`IndicEvaluator`** class — a documented evaluation helper that computes
  BLEU and chrF2++ scores (per the README summary).
- **Caveat:** the exact set of protected token types (numbers, URLs,
  emails, dates, named entities, etc.) and the exact regex/rules used are
  **not verified from primary source in this pass** (see above) — this
  project should read the actually-installed package's source
  (`site-packages/IndicTransToolkit/`) directly, or test empirically with
  representative inputs, before relying on it to interoperate with this
  project's own protected-content system rather than conflict with it.

## 3. Exact current version and installation

**Source:** PyPI JSON API (https://pypi.org/pypi/IndicTransToolkit/json),
fetched 2026-09-08.

- **Package name (PyPI):** `IndicTransToolkit`
- **Latest version found:** `1.1.1`
- **License (per PyPI metadata):** MIT
- **Python requirement:** `>=3.10`

Install methods (per the toolkit's own README, fetched 2026-09-08):
```bash
pip install indictranstoolkit
```
or, for development / editable install:
```bash
git clone https://github.com/VarunGumma/IndicTransToolkit
cd IndicTransToolkit
pip install --editable ./
```
(A search-result note indicated `--use-pep517` may be required for
`pip >= 25.0` when doing the editable install — unverified first-hand in
this pass, flag as a possible install-time gotcha to check if editable
install is chosen.)

Recommended dependency versions per the README: `numpy>=2.1`,
`torch>=2.5`, `transformers>=4.51` (older versions "may lack stability
guarantees" per the README's own wording as summarized).

### Platform support — important risk for this project

The toolkit's README explicitly states:

> "A Linux/MacOS based environment (This toolkit is not meant/built/tested
> for Windows as of now)."

(Source: https://github.com/VarunGumma/IndicTransToolkit, README, fetched
2026-09-08.)

**This is a direct risk for this project**, since the working environment
observed in this session is Windows (win32). This must be flagged to the
user/architecture decision: either (a) run the translation stage inside
WSL2/Linux, (b) run it in a Docker container, or (c) test empirically
whether it happens to work on native Windows anyway (unverified/unsupported
by the maintainer) before depending on it in production. Do not assume
native Windows compatibility without testing, per the CLAUDE.md stop rule.

## 4. Integration with IndicTrans2 — does the official usage example use it?

**Yes — confirmed directly from the official example.** See Section 1:
`AI4Bharat/IndicTrans2`'s own `huggingface_interface/example.py` imports
`IndicProcessor` from `IndicTransToolkit` and threads every translation
call through `preprocess_batch()` / `postprocess_batch()`. This is not a
third-party convenience wrapper bolted on after the fact from the
project's perspective — it is the path AI4Bharat itself documents and
demonstrates for HF-based inference.

## Known weaknesses / risks

1. **Not an AI4Bharat-org-owned repository**, despite being the
   AI4Bharat-endorsed/official-example-dependent tool — a governance risk
   (bus factor: one individual maintainer) worth noting in
   `docs/dependencies.md`.
2. **Explicitly unsupported on Windows** per the maintainer's own README —
   directly relevant since this project's development environment is
   Windows. Needs an explicit architecture decision (WSL2/Docker/Linux
   inference host) before depending on this toolkit in the translation
   layer.
3. **Exact entity/placeholder protection rules not independently verified
   from source** in this research pass (raw file fetch 404'd; Cython
   internals). Must be empirically tested (URLs, numbers, dates, mixed
   scripts) before trusting it to cooperate correctly with — rather than
   duplicate or conflict with — this project's own protected-content
   pipeline (CLAUDE.md's protected-region/placeholder architecture).
4. **Recency/version churn:** README recommends fairly recent minimum
   versions of `numpy`/`torch`/`transformers` (`>=2.1`/`>=2.5`/`>=4.51`),
   which should be checked for compatibility with whatever Python/torch
   stack this project standardizes on (see `dependency-verification`
   skill / `docs/dependencies.md`).
5. **Editable-install pip flag gotcha** (`--use-pep517` for `pip>=25.0`)
   was only found via a secondary/aggregated source, not confirmed
   first-hand in the README fetch — verify at actual install time.

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| IndicTransToolkit | GitHub repo README (VarunGumma) | https://github.com/VarunGumma/IndicTransToolkit | Community GitHub repo, but linked/endorsed by official AI4Bharat README | 2026-09-08 | README as of fetch date | Not AI4Bharat-org-owned; Windows unsupported; `IndicProcessor` API; install instructions; MIT license |
| IndicTransToolkit | Repo file tree | https://github.com/VarunGumma/IndicTransToolkit/tree/main | Community GitHub repo | 2026-09-08 | main branch | Confirms package layout (`IndicTransToolkit/` dir, `pyproject.toml`, `CHANGELOG.md`); Windows-unsupported statement; recommended `numpy`/`torch`/`transformers` versions |
| IndicTransToolkit | AI4Bharat/IndicTransToolkit (attempted) | https://github.com/AI4Bharat/IndicTransToolkit | Official org namespace check | 2026-09-08 | n/a | **404 Not Found** — confirms toolkit is NOT hosted under the AI4Bharat GitHub org |
| IndicTransToolkit | PyPI JSON metadata | https://pypi.org/pypi/IndicTransToolkit/json | Official package index (PyPI) | 2026-09-08 | 1.1.1 | Latest version 1.1.1, MIT license, requires Python >=3.10 |
| IndicTrans2 (for cross-reference) | Official README, migration note | https://raw.githubusercontent.com/AI4Bharat/IndicTrans2/main/README.md | Official GitHub repo (raw) | 2026-09-08 | main branch | Explicit statement that HF tokenizer was migrated to and is maintained in IndicTransToolkit |
| IndicTrans2 (for cross-reference) | huggingface_interface/example.py | https://github.com/AI4Bharat/IndicTrans2/blob/main/huggingface_interface/example.py | Official GitHub repo (source file) | 2026-09-08 | main branch | Confirms official example imports and uses `IndicProcessor` from IndicTransToolkit for pre/post-processing |
| IndicTrans2 (for cross-reference) | Model card: ai4bharat/indictrans2-en-indic-1B | https://huggingface.co/ai4bharat/indictrans2-en-indic-1B | Official HF model card | 2026-09-08 | 1B base, En-Indic | Official usage snippet also depends on `IndicProcessor`; mentions "entity replacement" in postprocessing |

See `docs/research/indictrans2.md` for the model-level findings.
