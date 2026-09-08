# IndicTrans2 Feasibility Gate — Milestone 5

Performed before any translation-architecture code was written, per
Milestone 5's explicit instruction. Sources are official
(AI4Bharat/IndicTrans2 and VarunGumma/IndicTransToolkit GitHub repos,
fetched via WebFetch during this milestone) plus direct measurement of
this project's own development machine — nothing here is from model
memory.

## Environment facts (measured directly, 2026-09-08)

| Fact | Value |
|---|---|
| OS | Windows 11 (Windows-11-10.0.26200-SP0), AMD64 |
| Python (Windows venv) | 3.12.4 |
| GPU | Intel(R) Iris(R) Xe Graphics (integrated) — **no discrete/CUDA-capable GPU** |
| CUDA availability | None |
| Windows C: free disk | ~25.5 GB free (of ~300 GB) |
| WSL | Present: Ubuntu (Noble, 24.04-based), version 2, state "Stopped" until invoked |
| WSL Python | 3.12.3 |
| WSL CPU | 8 logical cores |
| WSL RAM | 7.6 GiB total, 7.1 GiB available |
| WSL disk | 950 GB available on its own virtual disk |
| WSL `pip`/`ensurepip`/`python3-venv` | **Not installed** |
| WSL `sudo` | Requires an interactive password — **not available non-interactively in this session** |

## Official requirements (verified via WebFetch, not memory)

- **IndicTransToolkit README** (`github.com/VarunGumma/IndicTransToolkit`):
  > "We highly recommend using the latest versions of `numpy>=2.1`,
  > `torch>=2.5` and `transformers>=4.51`... We cannot guarantee the
  > stability of the module below these requirements."
  >
  > "A `Linux/MacOS` based environment (This toolkit is not
  > meant/built/tested for `Windows` as of now)."
- **IndicTrans2 HuggingFace interface README**
  (`github.com/AI4Bharat/IndicTrans2/blob/main/huggingface_interface/README.md`):
  IndicTransToolkit is a required dependency for the HF-compatible
  inference path — "automatically installed when you call
  `install.sh`" (a bash script, Linux-oriented).
- **Model identifiers** (HuggingFace, official):
  - Distilled (chosen for CPU feasibility): `ai4bharat/indictrans2-en-indic-dist-200M`,
    `ai4bharat/indictrans2-indic-en-dist-200M`
  - Base (not chosen — larger, GPU-oriented): `ai4bharat/indictrans2-en-indic-1B`,
    `ai4bharat/indictrans2-indic-en-1B`
- **Official inference API** (`huggingface_interface/example.py`,
  fetched directly): `IndicProcessor(inference=True)` +
  `ip.preprocess_batch(batch, src_lang=..., tgt_lang=...)` +
  `AutoTokenizer`/`AutoModelForSeq2SeqLM` (`trust_remote_code=True`) +
  `model.generate(..., min_length=0, max_length=256, num_beams=5,
  num_return_sequences=1)` + `tokenizer.batch_decode(...)` +
  `ip.postprocess_batch(generated_tokens, lang=tgt_lang)`. No sampling
  parameters (temperature/top-k/top-p) are set — beam search only, so
  generation is deterministic given fixed weights and eval-mode
  (dropout disabled).
- **Generation cap**: `max_length=256` tokens, confirmed directly in
  the official example code — matches this milestone's own stated
  "documents a maximum sequence length of 256 tokens" starting
  assumption exactly.

## Gate result

**Native Windows: NOT SUPPORTED**, per IndicTransToolkit's own explicit
statement — not attempted, per this milestone's instruction not to
force an unsupported install.

**WSL/Linux: hardware-feasible, but blocked by environment
provisioning in this session.** WSL Ubuntu is present with adequate
CPU (8 cores)/RAM (7.6 GiB, sufficient for a ~200M-parameter distilled
model on CPU)/disk (950 GB) — a genuinely supported environment per
IndicTransToolkit's own platform statement. However, this WSL image
has neither `pip` nor `python3-venv`/`ensurepip` installed, and
installing them requires `sudo apt install python3-venv` (or
equivalent), which requires an interactive password this
non-interactive session does not have and cannot supply. This is an
**environment-access blocker, not an IndicTrans2/PyTorch/Transformers
compatibility problem** — per Milestone 5's own instruction ("DO NOT
spend the milestone fighting the environment"), this was not pursued
further (e.g. by trying alternative provisioning routes) in this
session.

**Practical consequence:** the live IndicTrans2 experiment (point 8 —
translating real sentences across all 5 target language pairs) could
not be run in this session. Everything else Milestone 5 asks for was
built and is fully tested via the mock backend: the backend
abstraction, language registry, translation-unit builder, protected-
entity policy, long-input splitting, and an IndicTrans2 adapter that
is *code-complete and interface-tested* (import-safe, capability-gated
via `is_available()`, structured `TranslationBackendUnavailableError`
on missing dependencies) but not yet exercised against a real loaded
model.

## What would unblock the live experiment

Any of:
1. The user runs `sudo apt install -y python3-venv python3-pip` once
   in their own interactive WSL Ubuntu session (they have the sudo
   password; this session does not), after which
   `core/translation/indictrans2_backend.py`'s `IndicTrans2Backend()`
   should work as-is — no code changes anticipated, only environment
   provisioning.
2. A pre-provisioned Linux/WSL environment with pip already available
   is supplied.
3. A future session runs with sudo access.

Once unblocked, the concrete install/run sequence (from official
sources, not invented) would be:

```bash
python3 -m venv ~/it2_venv
source ~/it2_venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "numpy>=2.1" "transformers>=4.51" indictranstoolkit
```

then run `IndicTrans2Backend().translate(...)` from this project's
`core/translation/indictrans2_backend.py` directly — the adapter
already exists and needs no further code to attempt this once the
environment is provisioned.

## Decision

Per Milestone 5's explicit decision tree for this exact situation:
build the backend abstraction, mock backend, and isolated adapter (all
done); document the supported execution environment (this document);
run the real experiment only if available (attempted, genuinely
blocked by environment access, honestly reported as blocked rather
than skipped without trying). Architecture does not depend on Windows-
specific assumptions anywhere — confirmed by `core/translation/`
containing zero Windows-specific code paths.
