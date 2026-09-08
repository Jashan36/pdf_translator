# PDF Typography / Indic Script Shaping — Research Findings

Scope: Section I of the technical-research task. Verifies whether the
rendering approach (PyMuPDF) can correctly place translated Telugu,
Devanagari/Hindi, Tamil, Kannada, and Malayalam text, or whether
additional shaping technology is required.

Date checked: 2026-09-08.

---

## GO/NO-GO VERDICT (read this first)

> **PyMuPDF's `insert_text()` / `insert_textbox()` / `TextWriter` are NOT
> sufficient for Indic scripts. Additional shaping technology is
> required.** PyMuPDF itself ships the fix: `Page.insert_htmlbox()`
> (added in v1.23.8), which internally uses HarfBuzz for text shaping
> via a `Story` object. This is a **go, conditional on using
> `insert_htmlbox` (or an equivalent HarfBuzz-shaped path), never the
> classic text-insertion APIs**, for any Indic-script span.

Direct evidence, from the PyMuPDF maintainer (Jorj/Artifex) on the
project's own official GitHub Discussions (source-priority tier 2,
official repo):

> "You can **_never_** write Devanagari text using any of the methods
> `insert_text`, `insert_textbox` or `TextWriter`! Devanagari-based
> languages and many others need so-called 'text shaping' to correctly
> write them." — PyMuPDF Discussion #3568

> "Please use `insert_htmlbox`. This is the only way in PyMuPDF to
> write with text shaping." — PyMuPDF Discussion #3568

The official Artifex blog post about `insert_htmlbox` (tier 1/2,
Artifex is PyMuPDF's publisher) confirms the mechanism and the
version:

> `insert_htmlbox` was introduced in **PyMuPDF 1.23.8**. It lays out
> content via an internal `Story` object. The old methods are
> "effectively unusable for Hindi, Bengali, Tamil and more than 120
> other languages" because they lack complex-script support.
> PyMuPDF's `Story` class uses **HarfBuzz** for shaping, which
> correctly handles ligatures/reordering for these scripts.
> (artifex.com/blog/mastering-pdf-text-with-pymupdfs-insert-htmlbox-what-you-need-to-know)

A second official-repo discussion (#3659) adds a practical caveat: fallback
fonts are not supported by `insert_text()` at all, and even
`insert_htmlbox()` (HTML/CSS-driven) needs a font that actually
contains the target script's glyphs — a user reported that with the
wrong font choice, `insert_htmlbox()` can still fragment Indic
character sequences, while a well-supporting font (the maintainer
suggested "FiraGo" as an example that covers both Devanagari and
extended Latin, as an alternative to fonts with incomplete tables)
avoids this. **Font choice is not independent of shaping correctness**
— the font must have complete relevant OpenType tables (GSUB/GPOS) for
HarfBuzz to consume.

### What this means architecturally

- Do not use `page.insert_text`, `page.insert_textbox`, or raw
  `TextWriter` for any Telugu/Devanagari/Tamil/Kannada/Malayalam span.
- Use `page.insert_htmlbox()` (HTML+CSS input, HarfBuzz-shaped
  internally) as the PyMuPDF-native path for Indic text.
- Confirm empirically, once implementation starts, that the chosen
  Noto font's GSUB/GPOS tables produce correct conjuncts/reordering
  through `insert_htmlbox` for each target script (per Discussion
  #3659's font-choice caveat) — this is a "verify before trusting"
  item, not settled by this research pass alone.

---

## 1. What "complex text shaping" means for Indic scripts

Primary/authoritative sources: Unicode Standard Chapter 12 (Unicode
Consortium, the canonical spec for South and Central Asian scripts)
and the HarfBuzz project's own manual.

Unicode 16.0.0 core spec, Chapter 12, "Memory Representation and
Rendering Order" (unicode.org/versions/Unicode16.0.0/core-spec/chapter-12/):

> "the software that renders the Indic scripts must be able to
> reorder elements in mapping from the logical (character) store to
> the presentational (glyph) rendering"

> "When the dependent vowel [i-matra] is used to override the
> inherent vowel of a syllable, it is always written to the extreme
> left [of the consonant/cluster it modifies]" — even though it is
> **encoded in memory after** the consonant it visually precedes.

This is exactly the "vowel signs that visually appear before their
base consonant" behavior named in the task: Devanagari/Telugu-family
scripts store text in **phonetic (logical) order** but must be
**visually reordered** for correct rendering, and consonant clusters
are frequently rendered as **conjuncts** (merged glyph forms) rather
than as sequences of separate letters, controlled by the virama
character. A renderer that just maps one Unicode codepoint to one
glyph left-to-right (as simple Latin-style text insertion does) will
place vowel signs and cluster consonants in the wrong visual order and
show incorrect/half-formed glyphs.

## 2. HarfBuzz's role

Source: HarfBuzz official manual (harfbuzz.github.io), the project's
own docs — tier 1.

> "If you give HarfBuzz a font and a string containing a sequence of
> Unicode codepoints, HarfBuzz selects and positions the corresponding
> glyphs from the font, applying all of the necessary layout rules and
> font features." (harfbuzz.github.io/what-is-harfbuzz.html)

> HarfBuzz "can properly shape all of the world's major writing
> systems" and is "used directly by text-handling libraries like
> Pango, as well as by the layout engines in Firefox, LibreOffice, and
> Chromium." (harfbuzz.github.io/what-does-harfbuzz-do.html)

Supported script list per the same manual page includes explicit
per-script shapers for **Indic scripts (Devanagari, Bengali, Tamil,
Telugu, and others)**, Arabic-family, Southeast Asian scripts, plus a
Universal Shaping Engine fallback for others. HarfBuzz is confirmed as
the de-facto standard open-source shaping engine for producing correct
Indic glyph sequences from Unicode text + an OpenType font.

## 3. HarfBuzz vs FreeType — do not conflate

Per the same HarfBuzz manual page (tier 1, primary source):

> HarfBuzz "handles shaping only — it does not perform font
> rasterization (converting glyphs to pixels)." It is "designed and
> tested to run on top of the FreeType font renderer" — i.e. HarfBuzz
> decides *which glyphs, in what order, at what positions*; FreeType
> (or another rasterizer) then draws those glyph outlines to pixels /
> vector paths for output. They are complementary, not overlapping:
> shaping (HarfBuzz) happens before rasterization (FreeType). PyMuPDF
> itself is built on MuPDF, which uses FreeType-derived rendering
> internally for the actual glyph drawing once glyph IDs are known;
> HarfBuzz is the piece PyMuPDF's `Story`/`insert_htmlbox` path adds on
> top to get correct glyph IDs and positions for complex scripts in
> the first place.

## 4. PyMuPDF's text-insertion APIs — the core finding

See verdict above. Summary table of API behavior as documented on the
official PyMuPDF GitHub discussions/blog:

| API | Complex-script shaping? | Source |
|---|---|---|
| `page.insert_text()` | No — character-by-character placement, no reordering/conjuncts, no fallback fonts | PyMuPDF Discussion #3568, #3659 |
| `page.insert_textbox()` | No, same limitation | PyMuPDF Discussion #3568 |
| `TextWriter` | No, same limitation | PyMuPDF Discussion #3568 |
| `page.insert_htmlbox()` (>= v1.23.8) | Yes — internally shapes via HarfBuzz through a `Story` object | Artifex blog post; PyMuPDF Discussion #3659 |

## 5. What's needed instead / alternative approaches

Two viable paths, in order of preference for this project:

1. **Use `insert_htmlbox()`** — PyMuPDF's own documented, in-the-box
   answer. Requires composing the target text (with per-run
   font/size/color styling) as an HTML+CSS fragment and picking fonts
   with correct OpenType Indic tables. This keeps the whole pipeline
   inside PyMuPDF/MuPDF and avoids a second rendering engine
   dependency — matches the master plan's preference for deterministic,
   already-verified tooling. **This should be the default plan for
   the MVP.**
2. **Pre-shape with HarfBuzz directly (`uharfbuzz` Python bindings)
   and feed PyMuPDF pre-positioned glyph IDs** — this is the pattern
   other Python/PDF projects use when a target library (e.g. ReportLab,
   raw PDF content-stream writers) has no native shaping support at
   all: shape text externally into a glyph-ID + position stream, then
   place glyphs directly. This is more work and only needed if
   `insert_htmlbox()` proves inadequate for some construct in
   practice (verify empirically, don't assume).

Given PyMuPDF ships an in-box HarfBuzz-backed path, there is currently
no verified need to add a separate `uharfbuzz` dependency — but this
should be re-verified once real Telugu/Hindi/Tamil/Kannada/Malayalam
text is run through `insert_htmlbox()` and checked against expected
conjunct/reordering behavior (per the Development protocol's "verify
the output" step, not just documentation).

## 6. Noto fonts — license and availability

- Noto Sans/Serif Telugu, Devanagari, Tamil, Kannada, Malayalam are
  distributed by the official `notofonts` GitHub organization (e.g.
  github.com/notofonts/telugu, github.com/notofonts/devanagari,
  github.com/notofonts/tamil, github.com/notofonts/kannada — official
  per-script repos), and documented at the official Noto docs site
  notofonts.github.io/noto-docs.
- License: **SIL Open Font License (OFL) v1.1** — confirmed via the
  license text itself (checked on the archived `notofonts/noto-fonts`
  repo's LICENSE file, which carries the same OFL 1.1 text used across
  the Noto project). OFL 1.1 explicitly permits bundling into other
  software/documents ("Original or Modified Versions of the Font
  Software may be bundled, redistributed and/or sold with any
  software"), so embedding into a generated PDF is permitted; the only
  restriction is not selling the font **by itself** as a standalone
  product.
- This is compatible with the project's requirement of open-license,
  embeddable fonts for Indic scripts, and matches master plan Section
  22's fallback-font table naming ("Noto Sans Telugu", "Noto Sans
  Devanagari", etc.) as valid, currently-available font family names —
  not invented.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| PyMuPDF | "Devanagari... you can never write [it] using insert_text/insert_textbox/TextWriter" | https://github.com/pymupdf/PyMuPDF/discussions/3568 | Official GitHub repo (maintainer statement) | 2026-09-08 | current (post-1.23.8) | insert_text/insert_textbox/TextWriter cannot shape Devanagari; use insert_htmlbox |
| PyMuPDF | Mastering PDF Text with PyMuPDF's `insert_htmlbox` | https://artifex.com/blog/mastering-pdf-text-with-pymupdfs-insert-htmlbox-what-you-need-to-know | Official vendor (Artifex) blog | 2026-09-08 | insert_htmlbox introduced in v1.23.8 | insert_htmlbox uses HarfBuzz via Story object; old methods unusable for Hindi/Bengali/Tamil/120+ languages |
| PyMuPDF | Fallback fonts / insert_text limitations discussion | https://github.com/pymupdf/PyMuPDF/discussions/3659 | Official GitHub repo (maintainer + user reports) | 2026-09-08 | current | insert_text has no fallback-font support; insert_htmlbox needs a font with correct script coverage or it can still fragment glyphs |
| HarfBuzz | What is HarfBuzz? | https://harfbuzz.github.io/what-is-harfbuzz.html | Official project docs | 2026-09-08 | current (harfbuzz.github.io) | HarfBuzz selects/positions glyphs from a font for a Unicode string, applying layout rules/features |
| HarfBuzz | What does HarfBuzz do? | https://harfbuzz.github.io/what-does-harfbuzz-do.html | Official project docs | 2026-09-08 | current | Confirms HarfBuzz is shaping-only (no rasterization), runs on top of FreeType, supports Indic scripts explicitly |
| HarfBuzz | Shaping concepts | https://harfbuzz.github.io/shaping-concepts.html | Official project docs | 2026-09-08 | current | General definition of "complex scripts" requiring multiple shaping operations |
| Unicode Consortium | Unicode 16.0.0 core spec, Chapter 12 | https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-12/ | Official standard | 2026-09-08 | Unicode 16.0.0 | Authoritative description of logical-to-visual reordering of Indic dependent vowels and conjunct consonants via virama |
| Noto Fonts | notofonts GitHub organization (telugu/devanagari/tamil/kannada repos) | https://github.com/notofonts/telugu, https://github.com/notofonts/devanagari, https://github.com/notofonts/tamil, https://github.com/notofonts/kannada | Official project GitHub | 2026-09-08 | current | Official per-script repos exist and are actively maintained |
| Noto Fonts | Noto Fonts LICENSE (OFL 1.1) | https://github.com/notofonts/noto-fonts/blob/main/LICENSE | Official repo license file | 2026-09-08 | OFL v1.1 | Confirms open, embeddable license; bundling into other software/documents is explicitly permitted |
