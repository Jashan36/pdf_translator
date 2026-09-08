# Qwen3 via Ollama — Verified Findings and Role Evaluation

Date checked: 2026-09-08. Sources are the official Ollama library page and
tags page, the official Qwen3 GitHub repo (QwenLM/Qwen3), the official Qwen3
blog (qwenlm.github.io), the official Qwen3-8B model card on Hugging Face,
and the official Ollama API docs/blog. No prior/training knowledge was used
for any specific tag name, context length, or license claim below — all are
sourced per the technical-research skill's source-priority rules
(official docs > official GitHub > official model card > issue tracker >
community).

---

## H.1 Model sizes/variants actually available through Ollama right now

Per `ollama.com/library/qwen3` and `ollama.com/library/qwen3/tags`
(fetched 2026-09-08):

Base dense sizes: `qwen3:0.6b`, `qwen3:1.7b`, `qwen3:4b`, `qwen3:8b`,
`qwen3:14b`, `qwen3:32b`.
MoE sizes: `qwen3:30b` (alias `qwen3:30b-a3b`), `qwen3:235b` (alias
`qwen3:235b-a22b`).

Each size ships in multiple quantization/precision tags, e.g. for 8B:
`qwen3:8b`, `qwen3:8b-q4_K_M`, `qwen3:8b-q8_0`, `qwen3:8b-fp16`. Newer
"2507" refresh variants add explicit `-instruct` and `-thinking` tags, e.g.
`qwen3:4b-instruct-2507-q4_K_M`, `qwen3:4b-thinking-2507-q4_K_M`,
`qwen3:30b-a3b-instruct-2507-q4_K_M`, `qwen3:235b-a22b-thinking-2507-q4_K_M`.
`qwen3:latest` currently resolves to the 8b tag (5.2GB).

Note: Ollama also separately lists `qwen3.5`, `qwen3-vl` (vision-language),
`qwen3-embedding`, and `qwen3.6` as distinct library entries — these are
different model lines from base "qwen3" and are out of scope for this
research task, which was scoped to Qwen3 specifically.

## H.2 Context length limits per variant

There is a **documented discrepancy between two official sources** worth
flagging explicitly rather than picking one silently:

- **Ollama's library page** (ollama.com/library/qwen3, ollama.com/library/qwen3/tags)
  shows two context figures depending on tag: **40K** for the plain dense
  tags at default settings (0.6b, 1.7b, 8b, 14b, 32b, and 235b/30b default
  tags), and **256K** for the 4b, 30b, and 235b "2507"/refreshed tags and
  their `-instruct`/`-thinking` variants.
- **The official Qwen3 blog** (qwenlm.github.io/blog/qwen3/) states the
  *native* model context is 32K for the 0.6B-4B models and 128K for
  8B-32B and both original MoE models.
- **The official Qwen3 GitHub repo** (github.com/QwenLM/Qwen3) states the
  "Qwen3-2507" refresh models natively support 256K-token context, extendable
  to 1M tokens with additional techniques.
- **Qwen3-8B's official Hugging Face model card** states 32,768 tokens
  natively, extendable to 131,072 via YaRN scaling.

**Interpretation:** Ollama's listed context values reflect Ollama's runtime
default `num_ctx` per tag (which can differ from a model's native max and
can be raised at inference time up to the model's true ceiling), while the
model-card/GitHub figures describe the model's trained/native and
YaRN-extended ceilings. For this project, the practically relevant number is
**Ollama's served default context per tag** (40K for original dense tags,
256K for 2507-refresh tags), since that is what a local Ollama call will
actually honor without extra configuration — but the underlying model can
go higher if `num_ctx` is explicitly raised, up to the model's documented
native/YaRN ceiling. Do not assume a bare `qwen3:8b` pull gives you 256K
context by default — verify the specific tag's context field on the tags
page before relying on it.

## H.3 Documented multilingual capability — Indic language support

The official Qwen3 blog (qwenlm.github.io/blog/qwen3/) and the official
GitHub repo (github.com/QwenLM/Qwen3) both state Qwen3 supports **100+
languages and dialects** (GitHub says "100+", the blog and Alibaba's own
official X/Twitter post cite the more precise figure of **119 languages and
dialects**), spanning language families including Indo-European,
Sino-Tibetan, Afro-Asiatic, Austronesian, and **Dravidian**. The blog's
language-family breakdown explicitly names Indic languages including
**Hindi, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Marathi,
Oriya, Punjabi, and Assamese**.

Important caveat for this project: this is a claim about **instruction-
following and general multilingual capability being trained into the
model** ("strong capabilities for multilingual instruction following and
translation" — Qwen3-8B model card, huggingface.co/Qwen/Qwen3-8B). Neither
the blog, the GitHub repo, nor the model card publish **translation-quality
benchmarks specific to English→Telugu/Hindi/Tamil/Kannada** in what was
fetched. The claim of "119 languages supported" is a coverage/training-data
claim, not a documented translation-quality claim for these specific
language pairs. This distinction matters directly for the master-plan
question of whether Qwen3 should be trusted as a primary Indic translator
(see H.5below) — it should not be, absent project-specific benchmarking,
per the translation-quality skill's rule to test on this project's own
corpus rather than trust general-reputation claims.

## H.4 Structured output support (JSON mode / function calling) via Ollama's API

Per Ollama's official structured-outputs docs (docs.ollama.com/capabilities/structured-outputs,
via the official `ollama.com/blog/structured-outputs` announcement) and the
official API reference (github.com/ollama/ollama/docs/api.md):

- **JSON mode:** setting `"format": "json"` in a `/api/generate` or
  `/api/chat` request forces valid-JSON output; Ollama's own guidance is to
  also instruct the model in the prompt to emit JSON, to avoid excess
  whitespace/formatting artifacts.
- **JSON Schema (structured outputs):** passing a full JSON Schema object as
  the `format` field constrains the model's output to match that schema.
  Ollama's official recommendation is to build the schema via Pydantic
  (Python) or Zod (JS) rather than hand-writing it.
- **Tool/function calling:** both `/api/generate` and `/api/chat` accept a
  `"tools"` array of function definitions (name, description, JSON-Schema
  parameters); the model responds with a `"tool_calls"` field naming the
  invoked function and arguments, and results are fed back via a
  `"role": "tool"` message.

This is directly useful for this project's role 6 (protected-token
validation, a structured pass/fail-style check) and role 4 (semantic
classification into a constrained label set), both of which map cleanly
onto JSON-Schema-constrained output rather than free-text parsing.

## H.5 Ollama local HTTP API basics — streaming vs non-streaming

Per the official Ollama API docs (github.com/ollama/ollama/docs/api.md):
`/api/generate` and `/api/chat` stream by default, returning a sequence of
partial-response JSON objects with `"done": false` until the last object;
setting `"stream": false` returns one complete JSON response object instead,
including generation metadata (`total_duration`, `eval_count`, etc.). Both
modes are usable for this project — non-streaming is simpler for
programmatic use (e.g. a single paragraph-translation call awaiting a
complete JSON-schema response), streaming is preferable for any UI-facing
long-form generation (e.g. a Streamlit progress indicator during context
summarization of a long section).

## H.6 Approximate memory/VRAM requirements per model size

Ollama's library page reports on-disk model file sizes per tag, which are
the standard practical proxy for minimum RAM/VRAM headroom needed to load a
given quantization (actual runtime VRAM need is somewhat higher than file
size due to KV-cache and context-length overhead, which grows with `num_ctx`
and batch size — Ollama's docs do not publish a separate authoritative VRAM
formula, so file size is the best available official-source proxy here):

| Tag family | Representative `q4_K_M` size | fp16 size |
|---|---|---|
| 0.6b | 523MB | 1.5GB |
| 1.7b | 1.4GB | 4.1GB |
| 4b | ~2.5-2.6GB | 8.1GB |
| 8b | 5.2GB | 16GB |
| 14b | 9.3GB | 30GB |
| 30b-a3b (MoE) | 19GB | 61GB |
| 32b | 20GB | 66GB |
| 235b-a22b (MoE) | 142GB | 470GB |

For a "local-first, family-use" machine (this project's stated design
target), the 4b–8b range is the realistic ceiling on typical consumer
hardware without a discrete high-VRAM GPU; 14b+ requires a workstation-class
GPU or CPU RAM well in excess of what a typical family machine has, and
30b/235b MoE tags are effectively out of scope for this project's target
deployment despite their large active-context appeal.

## H.7 License

Both the official Qwen3 blog and the official GitHub repo state Qwen3's
open-weight models are released under **Apache 2.0** (github.com/QwenLM/Qwen3:
"All our open-weight models are licensed under Apache 2.0"; individual
license files are in each Hugging Face repo, confirmed on the Qwen3-8B
model card as `license: apache-2.0`). Apache 2.0 is a permissive license
compatible with this project's local-first, no-vendor-lock-in goals (master
plan Section 1, requirement 7: "Replaceable translation backends").

---

## Six-role evaluation

The master plan and CLAUDE.md are explicit that **IndicTrans2 is the primary
candidate for Indic-language translation quality**, and a local LLM
(Ollama/Qwen) is **for contextual reasoning and post-editing review, never
for PDF rendering or geometry decisions** (CLAUDE.md "Translation rule").
The evaluation below tests that stance against the evidence gathered above
rather than assuming it, per the instruction not to default to "Qwen should
be the translation engine."

| # | Role | Verdict | Evidence-based reasoning |
|---|---|---|---|
| 1 | Primary translation engine | **Should not** | Qwen3's official documentation claims broad language *coverage* (119 languages including Hindi/Telugu/Tamil/Kannada/etc.) but publishes no English→specific-Indic-language translation-quality benchmark in any source fetched here. IndicTrans2 is a model purpose-built and benchmarked specifically for Indic-language MT (per CLAUDE.md/master plan framing), which is a stronger evidentiary basis for a *primary* engine than a general-purpose multilingual LLM's coverage claim. Confirms the master plan's existing stance — this is not contradicted by anything found. |
| 2 | Translation review / post-editing (checking IndicTrans2 output for fluency/context issues) | **Should** | This role needs general reasoning and target-language fluency judgment, not certified translation-quality benchmarks — exactly what an instruction-tuned LLM with JSON-schema-constrained output (H.4) is suited for. Matches CLAUDE.md's stated intended use ("contextual reasoning and post-editing review"). Structured-output support means review results (e.g. flagged issues, confidence scores) can be returned in the translation-quality skill's checklist shape reliably. |
| 3 | Terminology extraction from source documents | **Should**, with validation | General-purpose instruction-following plus large context windows (up to 256K on 2507-refresh tags, H.2) make Qwen3 well-suited to scanning a document/section and proposing candidate glossary terms. This is a text-understanding task, not a translation-quality-critical task, so the "no Indic-benchmark" caveat from role 1 is far less relevant here — the extraction happens on source-language text. Validate extracted terms against the human-approved glossary tier (master plan Section 28) before use, same as any model-proposed content. |
| 4 | Semantic classification (heading vs paragraph vs caption) | **Should** | A closed-label classification task maps directly onto Ollama's JSON-Schema structured-output feature (H.4) — force the output into an enum of allowed roles. This is a well-scoped, low-risk use of a local LLM and does not touch translation quality or PDF geometry (respecting CLAUDE.md's core principle that geometry decisions stay deterministic — classification of *existing* extracted text blocks by role is a semantic decision, not a geometry decision). |
| 5 | Context summarization (building the document/section context package) | **Should** | Directly matches the translation-architecture design in this project (see `translation-architecture.md` G.2): a cheap once-per-section summary is exactly the kind of bounded, non-translation-quality-critical text-generation task suited to a local LLM, and the large context windows on 2507-refresh tags (up to 256K, H.2) comfortably fit a full section's text for summarization input. |
| 6 | Protected-token validation (confirming a token round-tripped correctly) | **Should**, but treat as a secondary check | This is fundamentally a string-equality/diff problem (does the output contain the exact placeholder/original span it should) — deterministic code (regex/string compare) is the more reliable primary mechanism, matching CLAUDE.md's "deterministic software preserves the document" principle. Qwen3 can serve as a secondary, structured-output-based sanity check (e.g. flagging suspicious near-matches like a mangled URL) via JSON-schema-constrained output (H.4), but should not be the sole or primary validator for a check that a simple string comparison already answers deterministically and more cheaply. |

**Overall confirmation:** the evidence gathered supports, rather than
challenges, the master plan/CLAUDE.md stance: Qwen3's own official
documentation makes a language-*coverage* claim, not a translation-*quality*
claim, for Indic languages specifically — there is no official Qwen
source claiming benchmarked strength on English→Telugu/Hindi/Tamil/Kannada
translation. That gap is exactly why IndicTrans2 (a model purpose-built and
presumably benchmarked for Indic MT per the master plan's framing) should
remain the primary translation candidate, with Qwen3-via-Ollama used for the
five supporting/reasoning roles above where general instruction-following
and structured output — not certified translation quality — is what's
needed.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| Ollama | Qwen3 library page | https://ollama.com/library/qwen3 | Official (Ollama library) | 2026-09-08 | qwen3 (current) | Lists available sizes 0.6b-235b, default context 40K for base tags / 256K for 2507-refresh tags, file sizes per tag. |
| Ollama | Qwen3 tags page | https://ollama.com/library/qwen3/tags | Official (Ollama library) | 2026-09-08 | qwen3 (current) | Full exact tag list incl. quantizations (q4_K_M/q8_0/fp16) and 2507 instruct/thinking variants; confirms exact tag names to use, e.g. `qwen3:8b`, `qwen3:30b-a3b-instruct-2507-q4_K_M`. |
| Qwen (Alibaba) | Qwen3: Think Deeper, Act Faster (official blog) | https://qwenlm.github.io/blog/qwen3/ | Official blog | 2026-09-08 | Qwen3 launch | States 8 models (2 MoE + 6 dense), native context 32K (0.6B-4B) / 128K (8B-32B + MoE), 119 languages/dialects incl. Hindi/Bengali/Tamil/Telugu/Kannada/Malayalam/Gujarati/Marathi/Oriya/Punjabi/Assamese, Apache 2.0 for dense models, tool-calling via Qwen-Agent/MCP. |
| Qwen (Alibaba) | QwenLM/Qwen3 GitHub repository | https://github.com/QwenLM/Qwen3 | Official GitHub repo | 2026-09-08 | Qwen3 (incl. 2507 refresh) | Confirms Apache 2.0 license for all open-weight models; Qwen3-2507 native 256K context, extendable to 1M; "100+ languages and dialects"; tool-use support across Ollama/vLLM/SGLang/llama.cpp/Transformers via Qwen-Agent. |
| Qwen (Alibaba) | Qwen/Qwen3-8B model card (Hugging Face) | https://huggingface.co/Qwen/Qwen3-8B | Official model card | 2026-09-08 | Qwen3-8B | 32,768 native / 131,072 via YaRN context; apache-2.0 license; "strong capabilities for multilingual instruction following and translation" (no Indic-specific benchmark given); no VRAM figures published on the card itself. |
| Alibaba/Qwen | Official Qwen X/Twitter post on language coverage | https://x.com/Alibaba_Qwen/status/1916962096346202468 | Official social (primary source, company account) | 2026-09-08 | Qwen3 launch | "Qwen3 models are supporting 119 languages and dialects" — corroborates blog's language-count claim from the model developer directly. |
| Ollama | Ollama API reference (api.md) | https://github.com/ollama/ollama/blob/main/docs/api.md | Official GitHub docs | 2026-09-08 | current | `/api/generate` and `/api/chat` stream by default (`"done": false` chunks) or return one object with `"stream": false`; `"format": "json"` / JSON-schema `format` field for structured output; `"tools"` array + `"tool_calls"` response for function calling. |
| Ollama | Structured outputs (blog + docs) | https://ollama.com/blog/structured-outputs and https://docs.ollama.com/capabilities/structured-outputs | Official blog/docs | 2026-09-08 | current | Confirms JSON-Schema-constrained structured output support in Ollama, recommends defining schema via Pydantic/Zod, add "return as JSON" to the prompt. |
| CLAUDE.md (internal) | Translation rule | `CLAUDE.md` | Project document | 2026-09-08 | n/a | States IndicTrans2 is the primary Indic-translation candidate and a local LLM (Ollama/Qwen) is for contextual reasoning/post-editing only, never rendering/geometry — the stance this research set out to confirm or challenge. |

