---
name: indic-language-translation
description: Verified facts and guardrails for translating into Indian languages (Telugu, Hindi, Tamil, Kannada, Malayalam, Marathi, etc.) — scripts, ISO/model language codes, IndicTrans2, Unicode/font fallback, sentence segmentation. Use whenever writing code or making claims involving an Indic language code, script, model, or font.
---

# Indic Language Translation

## The one rule that matters most

**Never guess an IndicTrans2 (or any translator's) language code from
memory.** Language-code schemes differ between projects (ISO 639-1 vs
639-3 vs script-qualified codes like `hin_Deva`, `tel_Telu`) and change
between model versions. Before writing a code that maps a language
name to a provider's language code:

1. Check the current official repository/docs for that exact provider
   (`technical-research` skill) — e.g. AI4Bharat's IndicTrans2 repo
   for its supported code list, not a general "Indic language codes"
   list from training data.
2. Record the source URL and date checked next to the mapping table in
   code (a comment, or `docs/dependencies.md`).
3. If the current docs are unreachable, say so explicitly and mark the
   mapping `UNVERIFIED` rather than filling it in from memory.

## Known-true facts (still verify before relying on for code)

- Priority languages per the master plan (Section 41 MVP scope):
  Telugu, Hindi, Tamil, Kannada.
- These use distinct Unicode script blocks (Telugu, Devanagari, Tamil,
  Kannada) — an English-only font (e.g. plain Helvetica) has no glyphs
  for any of them. See the font-fallback rule below.
- IndicTrans2 (AI4Bharat) is the plan's stated primary candidate for
  Indic translation quality (CLAUDE.md) — but confirm current
  supported-language list, model variants, licensing, and inference
  API from its repository before integrating, not from this file.

## Font fallback (mandatory for Indic scripts)

Master plan Section 22: the original font almost never contains
Telugu/Hindi/Kannada/Tamil glyphs. Do not attempt to force an
English-only font to render an unsupported script — use a
language-aware fallback table (e.g. Noto Sans/Serif per script) and
match weight (bold/italic) as closely as the fallback family allows.
Never silently fall back to tofu boxes or drop characters.

## Sentence segmentation and terminology

- Indic scripts have different sentence/word-boundary behavior than
  Latin scripts (e.g. no reliable whitespace-based word segmentation
  for some scripts/registers). Don't assume Python's default string
  splitting is linguistically correct — verify the segmentation
  approach the chosen translation backend expects.
- Respect the glossary/protected-terms precedence from the master plan
  (Section 28): protected terms > approved glossary > translation
  memory > translation model. Don't let a general-purpose translation
  call override a user-defined glossary entry.

## Transliteration vs translation

Brand names, proper nouns, and technical terms may need
transliteration (sound-preserving script conversion) rather than
translation (meaning conversion). Don't assume every source-language
token should be semantically translated — flag ambiguous cases for
human review rather than guessing which treatment is correct.

## When this applies

Any code or claim involving: a specific Indic language code, a
script-to-font mapping, IndicTrans2/IndicTransToolkit integration, or
segmentation/tokenization for an Indic language.
