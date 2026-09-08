---
name: translation-quality
description: Evaluate a translation as more than word-replacement — semantic fidelity, terminology consistency, numbers/units/named entities, grammar, and sentence structure. Use whenever writing translation-evaluation code, reviewing translation output, or comparing translation backends/models.
---

# Translation Quality

Translation ≠ word replacement. A translated string can be
"technically" a valid sentence in the target language and still be
wrong for this project's purposes. Evaluate along all of these axes,
not just fluency:

## Checklist

- **Semantic fidelity** — does it preserve the source meaning, not
  just plausible-sounding target-language words? Context matters more
  than the isolated sentence (master plan Section 6-7: use
  document/section/paragraph context, not sentence-by-sentence
  translation in isolation).
- **Numbers and units invariant** (Section 39). `600 IU` must not
  become `60 IU`. Extract numbers from source and translated text and
  compare normalized values — formatting/separators can localize,
  numeric meaning must not silently change.
- **Protected content untouched** (Section 9). URLs, emails, brand
  names, product codes, formulas, citations must survive translation
  unchanged — verify via the protected-token round-trip
  (tokenize → translate → restore), not by hoping the model leaves
  them alone.
- **Terminology consistency** — the same source term should map to
  the same target term throughout a document (glossary + translation
  memory, Section 27-28), not vary sentence to sentence.
- **Named entities** — people, places, organizations should not be
  mistranslated as common nouns or vice versa.
- **Grammar and sentence structure** in the target language —
  word-for-word structural transfer from the source language often
  produces ungrammatical or unnatural target text, especially between
  typologically different languages (e.g. English SVO vs. many Indic
  languages' SOV tendencies). Don't assume structural fidelity to the
  source sentence is the goal.
- **Untranslated / missing text** — flag spans that came back
  identical to the source (when they shouldn't be) or empty.

## Comparing translation backends/models

When asked to judge "should we use provider/model A or B here":

1. Don't answer from general reputation — run the checklist above
   against actual output on representative content from this
   project's test corpus (master plan Section 54).
2. Weight failures by consequence: a wrong number or a mistranslated
   protected term is more severe than an awkward but meaning-preserving
   sentence.
3. Record findings (what failed, on what input, which backend) rather
   than a bare verdict — this feeds the provider-selection decision in
   `PROJECT_STATE.md`.

## When this applies

Writing/reviewing semantic QA code (master plan Section 38-39),
choosing between translation providers, or evaluating any translated
output before it's considered acceptable for rendering.
