# Translation Architecture Over PDF Content

Status: research/synthesis, grounded against master plan Sections 5-9, 27-29
and external sources on document-level MT where available. This topic is
primarily a design-reasoning exercise built on the master plan's already-stated
hypothesis (paragraph/semantic-unit translation with layered context), not a
single tool lookup — tool/API claims below are individually sourced.

Date checked: 2026-09-08.

---

## G.1 Sentence vs paragraph vs block-level translation units for PDF localization

**Sentence-level in isolation (what the master plan explicitly calls the
"wrong approach", Section 6):**
- Breaks pronoun/anaphora resolution — a translator given only "It supports
  healthy development." has no antecedent for "It" and must guess gender/
  number/register in target languages that mark it (relevant for Telugu,
  Hindi, Tamil, Kannada, which have grammatical gender/case marking English
  lacks). The master plan's own iron example (Section 6) demonstrates this
  directly.
- Breaks terminology consistency across sentence boundaries — nothing forces
  "serving" to translate the same way in sentence N and sentence N+50 if each
  call sees no memory of prior choices, other than an external glossary/TM
  layer (Section 27-28) doing the enforcing out-of-band.
- Academic literature confirms the general failure mode: document-level MT
  survey work notes that "sentence-level and paragraph-level translations
  were well-explored... [but] less research was done on the document level,"
  and that classic sentence-independent NMT ("Sent2Sent") is the baseline
  that intersentential-context approaches are built to fix (arXiv 2101.11040,
  "A Comparison of Approaches to Document-level Machine Translation";
  Cambridge NLP survey "A survey of context in neural machine translation and
  its evaluation"). Community/academic tier — no single authoritative
  standard exists, but the direction of the finding is consistent across
  multiple papers.
- Safer only for: fully independent short strings with no surrounding
  discourse (e.g. a standalone button label, a copyright line) — i.e.
  exactly the protected/atomic content the master plan already carves out
  separately (Section 9), not body prose.

**Paragraph-level (master plan's stated preferred unit, Section 8):**
- Matches the "preferred translation unit" list already in the plan:
  paragraph, heading, table cell, caption, list item.
- Resolves most intra-paragraph anaphora and keeps sentence order and
  local discourse markers intact, since the whole paragraph is one
  translation call.
- Research supports this directly: extending the NMT input unit from
  sentences to ~1000 subword tokens (paragraph/document-scale) produced
  "strong performance gains... over sentence-level baselines," and a
  documented trend is "to use paragraphs instead of sentences as segments"
  (arXiv 2101.11040). This is squarely a paragraph-level (not whole-document)
  finding, i.e. it validates the master plan's chosen unit rather than
  arguing for going further.
- Google's own Cloud Translation Advanced documentation states that when a
  paragraph is sent, "Cloud Translation translates the whole paragraph at
  once instead of translating each sentence one at a time" — i.e. a shipped
  commercial system uses paragraph as its translation-context unit, not
  sentence or whole document (docs.cloud.google.com/translate/docs/intro-to-v3,
  checked 2026-09-08).
- Risk: a paragraph is still a rendering-adjacent unit in a PDF — it may
  span multiple visual spans with different fonts/bold runs (the plan's own
  "Healthy " + "food " + "choices" example, Section 8) and, more importantly
  for layout math, paragraph-level translation produces one translated
  string whose length must be re-flowed across the *original* multi-span,
  multi-line bounding geometry. This is a rendering-layer problem the plan
  already assigns to the fit/layout stage (Section 3B), not a reason to
  avoid paragraph units.

**Whole-block / whole-document as one string:**
- Not recommended and not what any cited production system does at
  translation-call granularity. Google's document translation product
  translates a formatted *file* end-to-end as a service capability (preserves
  file-level layout, docs.cloud.google.com/translate/docs/advanced/translate-documents)
  but this is a black-box document API, not evidence that a single
  giant-string LLM/MT call per whole document is the right *unit of
  translation* for a system that needs per-element bounding boxes back —
  the whole point of this project's own reconstruction pipeline (master plan
  Section 3B/8) is that translated text must map back to individual
  text-object bboxes, which a monolithic whole-document translation output
  cannot cleanly provide without re-segmentation (introducing exactly the
  alignment problem the paragraph-unit design avoids).
- NLLB's own model card is explicit that the research model "is not intended
  for production deployment... or document translation" and "notes
  limitations on long inputs" (master plan Section 13, huggingface.co/facebook/nllb-200-3.3B)
  — direct evidence against feeding very long/whole-document spans into at
  least that specific model family.

**Verdict:** Paragraph (and paragraph-equivalent structural units — heading,
table cell, caption, list item, as already stated in Section 8) is the
correct translation unit. Sentence-only isolation should never be the sole
context given to the translator; whole-document-as-one-call should not be
the *unit of translation* even though document-level *context* should
inform each call (see G.2).

---

## G.2 Carrying document/section context without resending the whole PDF every call

The master plan already specifies the shape of this (Section 6-7): a layered
context of Document → Section → Paragraph → Current unit, packaged per call
as a bounded JSON object with `document_purpose`, `audience`, `section`,
`previous_context`, `current_text`, `following_context`, `glossary`,
`protected_terms`, `layout_constraints` (Section 7). This is architecturally
sound and matches the general shape of what's documented externally,
though no single "reference implementation" of this exact pattern is
published by a vendor — it should be treated as a project-specific design
validated against general document-MT principles, not a copied pattern.

Supporting evidence for the general approach (not for this exact JSON shape,
which is project-specific):
- Google Cloud Translation's **Adaptive Translation** feature explicitly
  supports "a limited number of example translation pairs, optionally in
  multi-sentence context windows" to customize translation without resending
  the whole corpus per call (docs.cloud.google.com/translate/docs/intro-to-v3) —
  i.e. a production system also solves "carry context without full resend"
  by passing a small, curated context window plus reference examples, not
  the entire document.
- Academic work on LLM-based document MT explores the same cost/quality
  tradeoff directly: "Efficiently Exploring Large Language Models for
  Document-Level Machine Translation with In-Context Learning" (arXiv
  2406.07081) and "Source-primed Multi-turn Conversation Helps Large
  Language Models Translate Documents" (arXiv 2503.10494) — both propose
  giving the model a *summarized or partial* document context (primed once,
  or as a bounded window) rather than the full document text on every
  translation unit. This validates the general strategy — build a compact,
  reusable context package and reuse/slide it — as directionally consistent
  with published approaches, at community/research tier of confidence.

**Recommended concrete mechanism (extending the plan's Section 7 shape):**
1. Compute a **document-level context object once per document**
   (purpose, audience, tone, source/target language) — cheap, reused
   unchanged across every translation call, never resent as raw document
   text.
2. Compute a **section-level context summary once per section** (not full
   section text) — e.g. 1-3 sentence gist of what the section is about,
   the running glossary terms already used in that section. This is where
   a local LLM's summarization role fits (see qwen3-ollama.md, role 5).
3. Pass only **local sliding-window paragraph context** per call —
   previous paragraph (or last N sentences) and next paragraph (or first N
   sentences) verbatim, as the plan's Section 7 already does with
   `previous_context`/`following_context`.
4. Never resend: full document text, full section text, or the full
   translation memory table. Only resend the fixed document object, the
   cheap section summary, and the local paragraph window.

This keeps prompt size roughly constant regardless of document length
(bounded by the sliding window + fixed summaries), which is the practical
answer to the cost/quality tradeoff the task asks about.

---

## G.3 Glossary precedence, translation memory, and protected-token round-tripping in a paragraph-level pipeline

The master plan already specifies (Sections 9, 27, 28):
- Protected-token tokenize → translate → restore round-trip (Section 9),
  with explicit before/after examples.
- Translation memory keyed by exact source string + target language,
  reused when the same phrase recurs (Section 27).
- Glossary precedence order: `protected terms > approved glossary >
  translation memory > translation model` (Section 28).

**Is this documented/recommended elsewhere, or project-specific?**
- The general *pattern* of tokenizing protected spans before sending text to
  any MT engine and restoring them afterward is a long-standing,
  widely-used technique in commercial CAT/MT tooling (glossary "do not
  translate" lists, placeholder/tag protection) — this is standard industry
  practice, not a novel invention, though we did not find one single
  official spec document naming it exactly this way for a generic MT API.
  This project's translation-quality skill already encodes the same
  requirement independently (`.claude/skills/translation-quality/SKILL.md`:
  "verify via the protected-token round-trip (tokenize → translate →
  restore), not by hoping the model leaves them alone").
- Google Cloud Translation Advanced's glossary feature is the closest
  documented commercial analogue: it lets you supply a controlled
  term-mapping file that the API is instructed to honor during translation
  (docs.cloud.google.com/translate/docs/advanced/translate-documents
  references glossary support for document translation). This validates
  "glossary overrides model output" as an existing, documented pattern —
  it does not, on its own, validate the *exact* four-tier precedence order
  (protected > glossary > TM > model) the master plan specifies; that
  ordering is a project-specific design choice and should be validated by
  this project's own QA process (translation-quality skill checklist) rather
  than cited to an external source.
- **Soundness check on the precedence order itself:** the order is logically
  defensible — protected terms must never be touched regardless of glossary
  entries (a URL should not be "glossary-translated"); an approved
  human-curated glossary term should outrank a memory entry that may have
  been produced by an earlier, possibly-uncorrected model call; translation
  memory (previously produced and presumably reviewed/approved output)
  should outrank asking the model fresh each time, for consistency. No
  external source contradicts this ordering; it is recommended to validate
  it in this project's own tests using the translation-quality skill's
  checklist (numbers/units invariant, protected content untouched,
  terminology consistency) rather than treating it as externally proven.
- **Paragraph-level-specific consideration not explicit in the plan:** when
  tokenizing protected spans inside a paragraph (not a single span), token
  placeholders must survive being embedded in a longer, syntactically real
  sentence context — verify placeholders (i) don't get mistaken for content
  words the model tries to "translate" or transliterate, and (ii) don't
  break the model's sentence segmentation in a way that garbles surrounding
  word order on restoration. This is exactly the round-trip verification the
  translation-quality skill and master plan Section 39 already call for; it
  should be tested empirically against whichever backend is chosen (this is
  a testing/validation task, not something citable to an external doc).

---

## G.4 Numbers, units, and named entities given a paragraph-level unit

- **Numbers and units:** the master plan (Section 39, referenced in the
  translation-quality skill) already requires that numeric meaning must not
  silently change (`600 IU` must not become `60 IU`), verified by extracting
  numbers from source and translated text and comparing normalized values —
  this is a **verification/QA strategy**, not necessarily a translation-time
  protection strategy. Two documented options exist:
  1. Protect-tokenize numbers/units like URLs (guarantees literal
     preservation, but risks awkward target-language number/unit ordering —
     many languages localize digit grouping, decimal separators, or unit
     placement, e.g. Indic numbering conventions differ from Western
     thousand-separators — which a fully protected token would prevent from
     localizing correctly).
  2. Let the translator/model translate numbers+units normally but validate
     post-hoc via the numeric-extraction-and-compare check the plan already
     specifies (Section 39) — this preserves localization ability (correct
     digit grouping, unit-name translation e.g. "IU" often stays as-is but
     "grams" may need to localize) while still catching corruption.
  **Recommendation:** do NOT blanket protect-tokenize plain numbers/units
  the way URLs/brand names are protected — protect only identifiers that
  must be byte-identical (URLs, emails, product codes, ISBNs, formulas,
  per Section 9's own list, which conspicuously does NOT include plain
  numbers/units). Instead, rely on the master plan's already-specified
  post-hoc numeric QA check (Section 39) to catch corruption, since that is
  what the plan and the translation-quality skill both already converge on.
  This is a validated-for-soundness project design, not something with one
  canonical external citation — no single official source was found saying
  "protect numbers as tokens" or "don't"; the QA-based approach is more
  consistent with the plan's own existing Section 39 mechanism and with
  general MT practice of letting the model handle numeral localization.
- **Named entities:** protect-tokenize only entities that must not be
  translated/transliterated by policy (Section 9's brand names, legal
  identifiers, citations). For entities that *should* be transliterated
  (person/place names in running Indic-language prose, which is normal and
  expected, not an error), do not protect-tokenize — rely on the
  translation-quality skill's checklist item "Named entities — people,
  places, organizations should not be mistranslated as common nouns or vice
  versa," verified by human/LLM-assisted review rather than by forcing
  literal preservation, since forcing literal preservation of a
  person/place name would actually be *wrong* in many Indic-script target
  languages (a name typically gets transliterated into the target script,
  not left in Latin script).

---

## Recommended translation-unit architecture (synthesis)

1. **Unit of translation:** paragraph-equivalent structural block (paragraph,
   heading, table cell, caption, list item), matching master plan Section 8 —
   confirmed as consistent with the one production system found to document
   its context-window granularity (Google Cloud Translation Advanced
   translates whole paragraphs at once) and with academic findings that
   paragraph/document-scale context measurably beats sentence-independent
   translation.
2. **Context carried per call:** a three-layer, bounded context package —
   (a) a fixed, once-computed document object (purpose/audience/tone/
   languages), (b) a cheap once-computed per-section summary (not full
   section text), and (c) a local sliding window of the immediately
   preceding/following paragraph — matching and slightly extending the
   plan's Section 7 JSON shape. This bounds prompt cost independent of
   document length, mirroring the general strategy documented in
   context-window-limited academic LLM-document-MT work.
3. **Protected-span handling:** tokenize-before-translate/restore-after only
   for the master plan's Section 9 list (URLs, emails, brand names, product/
   legal identifiers, formulas, code, ISBNs, citations) — a standard,
   industry-consistent pattern, validated by this project's own
   translation-quality skill's round-trip requirement. Do not extend
   protection to plain numbers/units or to entities that should be
   transliterated; instead catch corruption via the numeric-normalization QA
   check the plan already specifies (Section 39).
4. **Glossary/TM precedence:** keep the plan's stated order (protected >
   glossary > TM > model) — logically sound and not contradicted by any
   external source found; validate empirically per-document via the
   translation-quality skill's checklist rather than treating the order as
   externally proven.
5. **Rendering separation preserved:** paragraph-level translated output
   must be mapped back to the original multi-span bounding-box geometry by
   the deterministic rendering layer (master plan Section 3B), never by
   asking the model to reason about layout — this is unaffected by unit
   choice and remains a hard boundary per CLAUDE.md's core principle.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| Master plan (internal) | Local PDF Language Converter — Technical Master Plan, Sections 5-9, 27-29 | `local_pdf_localizer_technical_master_plan.md` | Project document | 2026-09-08 | n/a | Defines paragraph-preferred translation unit, layered context package, protected-token pattern, glossary/TM precedence — the design this research validates. |
| Google Cloud Translation | Cloud Translation Advanced details | https://docs.cloud.google.com/translate/docs/intro-to-v3 | Official docs | 2026-09-08 | current (v3 Advanced) | "Cloud Translation translates the whole paragraph at once instead of translating each sentence one at a time"; Adaptive Translation supports multi-sentence context windows with example pairs instead of full-corpus resend. |
| Google Cloud Translation | Translate documents | https://docs.cloud.google.com/translate/docs/advanced/translate-documents | Official docs | 2026-09-08 | current | Document Translation API preserves formatting/layout for PDF/DOCX and supports glossaries; online PDF limit up to 20 MB / 300 pages. |
| Document-level MT (survey) | A survey of context in neural machine translation and its evaluation | https://www.cambridge.org/core/journals/natural-language-processing/article/survey-of-context-in-neural-machine-translation-and-its-evaluation/875C3E2DEAAB8845A0F05988D5A18B55 | Peer-reviewed | 2026-09-08 | n/a | Sentence-independent NMT is the baseline that intersentential-context methods aim to fix; describes taxonomy of context-incorporation approaches. |
| Document-level MT | A Comparison of Approaches to Document-level Machine Translation | https://arxiv.org/pdf/2101.11040 | Preprint (academic) | 2026-09-08 | arXiv 2101.11040 | Extending NMT input to ~1000 subword tokens (paragraph/doc scale) gave strong gains over sentence-level baselines; notes trend toward paragraph-sized segments (Doc2Doc, Doc2Sent approaches). |
| Document-level MT (LLM) | Efficiently Exploring LLMs for Document-Level MT with In-context Learning | https://arxiv.org/html/2406.07081v1 | Preprint (academic) | 2026-09-08 | arXiv 2406.07081 | Explores giving LLMs bounded/partial document context via in-context learning rather than full-document resend per call. |
| Document-level MT (LLM) | Source-primed Multi-turn Conversation Helps LLMs Translate Documents | https://arxiv.org/html/2503.10494 | Preprint (academic) | 2026-09-08 | arXiv 2503.10494 | Proposes priming an LLM once with document context in a multi-turn conversation rather than resending full text per translation unit — supports the "compute once, reuse" context strategy. |
| NLLB (Meta) | facebook/nllb-200-3.3B model card | https://huggingface.co/facebook/nllb-200-3.3B | Official model card | 2026-09-08 | 3.3B checkpoint | Explicitly disclaims production/document-translation use and notes long-input limitations — cited already in master plan Section 13, corroborated here. |
| Translation-quality skill (internal) | translation-quality SKILL.md | `.claude/skills/translation-quality/SKILL.md` | Project document | 2026-09-08 | n/a | Independently specifies protected-token round-trip verification and numeric-invariance checking — used here to justify QA-based (vs. blanket-tokenize) handling of numbers/units. |

