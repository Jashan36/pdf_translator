# Indic Rendering Proof-of-Concept

Experimentally verifies `docs/research/EXPERIMENTS.md` #1: does
PyMuPDF + `page.insert_htmlbox()` + Noto fonts correctly shape and
bound Indic Unicode text? This is the go/no-go gate for Milestone 2
(per `PROJECT_STATE.md`) — Document Model implementation does not
proceed until this is resolved one way or the other.

Script: `scripts/experiments/indic_rendering_proof.py`. Raw output:
`docs/research/assets/indic-rendering/` (per-language full-page PNGs,
per-case crops, a PDF per language, and `results.json` with every
`spare_height`/`scale` value).

## ENVIRONMENT

- PyMuPDF version: **1.28.2** (`pymupdf.VersionBind`)
- Python: 3.12.4 (project `.venv`)
- OS: Windows 11 (dev machine)
- API used: `page.insert_htmlbox(rect, html, css=css, archive=archive, scale_low=1.0)`
- Redaction/replacement APIs (`add_redact_annot`/`apply_redactions`) not
  exercised in this proof — this is purely an insertion/shaping test,
  per the instructed scope.

## FONTS

Downloaded from the official `google/fonts` mirror of the `notofonts`
project (variable TTFs, confirmed identical upstream source per
`docs/research/pdf-typography.md`), license OFL 1.1 (confirmed via
`OFL.txt` alongside each font in that repo):

| Language | Font file | Source |
|---|---|---|
| Telugu | `fonts/telugu/NotoSans-telugu.ttf` | github.com/google/fonts/tree/main/ofl/notosanstelugu (`NotoSansTelugu[wdth,wght].ttf`) |
| Hindi (Devanagari) | `fonts/devanagari/NotoSans-devanagari.ttf` | github.com/google/fonts/tree/main/ofl/notosansdevanagari |
| Tamil | `fonts/tamil/NotoSans-tamil.ttf` | github.com/google/fonts/tree/main/ofl/notosanstamil |
| Kannada | `fonts/kannada/NotoSans-kannada.ttf` | github.com/google/fonts/tree/main/ofl/notosanskannada |

All four confirmed as valid variable TrueType fonts with a `GDEF`
table present (glyph-definition table, required for OpenType Layout
shaping) via `file` command inspection at download time. Font
embedding: `pymupdf.Archive(font_dir)` passed to `insert_htmlbox`,
referenced via `@font-face { src: url(<filename>) }` in the CSS — no
issues loading any of the four.

## HTML/CSS TEMPLATE

Identical structure for every test case, only the font-family/file and
inner text changed:

```css
@font-face {font-family: NotoSansTelugu; src: url(NotoSans-telugu.ttf);}
* {font-family: NotoSansTelugu; font-size: 16px;}
```

```html
<p>{test text}</p>
```

Rect widths: full text-column width (515pt). Rect heights deliberately
tight (40pt for word/sentence/punctuation/numerals, 55pt for mixed,
90pt for paragraph) so overflow/clipping would be visible if it
occurred — see `CASE_HEIGHT` in the script.

## TEST MATRIX

6 cases × 4 languages = 24 renders. Real Unicode text (not
transliteration) for every case — see the script for exact strings.
Content is illustrative test text chosen to exercise conjuncts, vowel
reordering, punctuation, native digits, and mixed-script runs; it is
not vetted for natural fluency (that's out of scope for a shaping
test).

---

## RESULTS BY LANGUAGE

### Telugu

- **INPUT**: word `నమస్కారం`; sentence `ఇది ఒక పరీక్ష వాక్యం.`; paragraph
  (3 sentences, conjunct-heavy: `ఆరోగ్యానికి`, `సమతుల్య`, `శరీరానికి`);
  punctuation `మీరు బాగున్నారా? అవును, నేను బాగున్నాను! (ధన్యవాదాలు)`;
  numerals `ఉష్ణోగ్రత 37°C మరియు ధర ₹500. సంఖ్య: ౧౨౩౪౫ (12345)`; mixed
  `COVID-19 మహమ్మారి ప్రపంచాన్ని మార్చింది. WHO మార్గదర్శకాలను జారీ చేసింది.`
- **RESULT**: word/sentence/punctuation/mixed rendered with correct
  conjunct formation (క్ష, ష్ట్ర, ర్గ, న్న all correctly stacked/formed)
  and correct vowel-sign placement. Paragraph wrapped at a word
  boundary (not mid-syllable) and fit with 19.6pt spare height. Mixed
  English+Telugu run rendered both scripts correctly in one line, no
  visual glitch at the script boundary. **Western-digit numerals
  (37, 500, 12345) rendered correctly.** **Native Telugu digits
  (౧౨౩౪౫) rendered as wrong/garbled glyphs** — see FAILURE below.
- **FAILURE**: Native Telugu digit codepoints (U+0C67-U+0C6B) render
  as incorrect glyphs instead of the intended digit shapes. Isolated
  by direct testing (see "Root Cause Isolation" below) to a PyMuPDF
  text-insertion glyph-selection bug for this codepoint range in this
  font — not the font, not shaping, not the HTML/CSS layer.
- **SCREENSHOT**: `docs/research/assets/indic-rendering/telugu_all_cases.png`
  (composite), `telugu_numerals.png` (failure case, cropped).
- **spare_height/scale** (from `results.json`): word 0.0/1.0, sentence
  0.0/1.0, paragraph 19.6/1.0, punctuation 0.0/1.0, numerals 0.0/1.0,
  mixed 3.8/1.0. No case reported `spare_height == -1` (PyMuPDF's own
  clipped-content signal), and no case needed `scale < 1.0`.
- **CONCLUSION**: **PASS WITH LIMITATIONS.** Core shaping (conjuncts,
  reordering, wrapping, mixed-script) is correct. Native-digit
  rendering is broken but has a zero-cost mitigation (use Western
  digits, see below).

### Hindi (Devanagari)

- **INPUT**: word `नमस्ते`; sentence `यह एक परीक्षण वाक्य है।`; paragraph
  (conjunct/reph-heavy: `स्वास्थ्य`, `संतुलित`, `विशेष रूप`); punctuation
  `क्या आप ठीक हैं? हाँ, मैं ठीक हूँ! (धन्यवाद)`; numerals `तापमान 37°C
  और कीमत ₹500 है। संख्या: १२३४५ (12345)`; mixed `COVID-19 महामारी ने
  दुनिया को बदल दिया। WHO ने दिशानिर्देश जारी किए।`
- **RESULT**: All six cases rendered correctly, including the hardest
  shaping cases in this whole test: conjunct stacking (`स्वास्थ्य`,
  `संतुलित`), the candrabindu diacritic (`हूँ`), and — notably — the
  **native Devanagari digits (१२३४५) rendered correctly**, unlike the
  other three scripts. Paragraph wrapped correctly at a word boundary
  with 19.6pt spare height. Mixed English+Hindi rendered cleanly in
  one line.
- **FAILURE**: None found.
- **SCREENSHOT**: `docs/research/assets/indic-rendering/devanagari_all_cases.png`.
- **spare_height/scale**: word 0.0/1.0, sentence 0.0/1.0, paragraph
  19.6/1.0, punctuation 0.0/1.0, numerals 0.0/1.0, mixed 3.8/1.0. No
  clipping, no forced scaling.
- **CONCLUSION**: **PASS.** No limitations found in this test matrix.

### Tamil

- **INPUT**: word `வணக்கம்`; sentence `இது ஒரு சோதனை வாக்கியம்.`;
  paragraph (`ஆரோக்கியத்திற்கு`, `குழந்தைகளுக்கு`); punctuation `நீங்கள்
  நலமா? ஆம், நான் நலமாக இருக்கிறேன்! (நன்றி)`; numerals `வெப்பநிலை 37°C
  மற்றும் விலை ₹500. எண்: ௧௨௩௪௫ (12345)`; mixed `COVID-19 தொற்றுநோய்
  உலகை மாற்றியது. WHO வழிகாட்டுதல்களை வெளியிட்டது.`
- **RESULT**: word/sentence/punctuation/paragraph/mixed all rendered
  with correct Tamil conjunct/ligature formation and correct wrapping.
  Western-digit numerals correct. **Native Tamil digits (௧௨௩௪௫)
  rendered as actual Tamil consonant letters (`க உ ங ச ரு`) instead of
  digit glyphs** — a more severe version of the same class of bug seen
  in Telugu.
- **FAILURE**: Same class as Telugu — isolated below to PyMuPDF's
  glyph-selection step, not the font or shaping engine.
- **SCREENSHOT**: `docs/research/assets/indic-rendering/tamil_all_cases.png`,
  `tamil_numerals.png` (failure case).
- **spare_height/scale**: word 0.0/1.0, sentence 0.0/1.0, paragraph
  0.4/1.0, punctuation 0.0/1.0, numerals 0.0/1.0, mixed 0.0/1.0. No
  clipping, no forced scaling (paragraph fit tighter than other
  languages — only 0.4pt spare — but still fit within `scale_low=1.0`).
- **CONCLUSION**: **PASS WITH LIMITATIONS.** Same mitigation as Telugu.

### Kannada

- **INPUT**: word `ನಮಸ್ಕಾರ`; sentence `ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯ.`;
  paragraph (`ಆರೋಗ್ಯಕ್ಕೆ`, `ಮಕ್ಕಳಿಗೆ`); punctuation `ನೀವು ಚೆನ್ನಾಗಿದ್ದೀರಾ?
  ಹೌದು, ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ! (ಧನ್ಯವಾದಗಳು)`; numerals `ಉಷ್ಣಾಂಶ 37°C ಮತ್ತು
  ಬೆಲೆ ₹500. ಸಂಖ್ಯೆ: ೧೨೩೪೫ (12345)`; mixed `COVID-19 ಸಾಂಕ್ರಾಮಿಕ
  ಜಗತ್ತನ್ನು ಬದಲಾಯಿಸಿದೆ. WHO ಮಾರ್ಗಸೂಚಿಗಳನ್ನು ಬಿಡುಗಡೆ ಮಾಡಿದೆ.`
- **RESULT**: word/sentence/punctuation/paragraph/mixed all rendered
  with correct conjunct formation and wrapping. Western-digit numerals
  correct. **Native Kannada digits (೧೨೩೪೫) rendered incorrectly** —
  same bug class as Telugu/Tamil.
- **FAILURE**: Same class, same root cause (isolated below).
- **SCREENSHOT**: `docs/research/assets/indic-rendering/kannada_all_cases.png`,
  `kannada_numerals.png` (failure case).
- **spare_height/scale**: word 0.0/1.0, sentence 0.0/1.0, paragraph
  19.6/1.0, punctuation 0.0/1.0, numerals 0.0/1.0, mixed 0.0/1.0. No
  clipping, no forced scaling.
- **CONCLUSION**: **PASS WITH LIMITATIONS.** Same mitigation as Telugu.

---

## ROOT CAUSE ISOLATION (native-digit failure)

Found in 3 of 4 languages (Telugu, Tamil, Kannada — not Devanagari).
Isolated through a sequence of targeted checks, not guessed:

1. **Ruled out: my input text.** Read the script file's own bytes back
   and confirmed the exact Unicode code points on disk match the
   intended digit characters (e.g. Tamil `௧௨௩௪௫` = U+0BE7…U+0BEB,
   confirmed correct per the Unicode Tamil block) — not a copy/paste
   corruption.
2. **Ruled out: font glyph coverage.** `pymupdf.Font(fontfile=...).has_glyph(codepoint)`
   returns a valid, distinct glyph ID for every native digit codepoint
   tested (e.g. Tamil digit one → glyph ID 56, distinct from letter
   'ka' → glyph ID 18). `Font.unicode_to_glyph_name(codepoint)`
   correctly reports `"TAMIL DIGIT ONE"`, `"TELUGU DIGIT ONE"`,
   `"KANNADA DIGIT ONE"` for the respective fonts — the font data and
   PyMuPDF's own font-parsing layer agree on what these codepoints
   should map to.
3. **Ruled out: HTML/CSS layer specifically.** Re-rendered the same
   Tamil digit string via the plain `page.insert_text()` API (no
   HTML/CSS, no `Story` object, no HarfBuzz shaping path at all) using
   the same font file directly — **the wrong glyphs appeared again,
   identically.** This rules out `insert_htmlbox`'s CSS/story engine as
   the cause, since the bug reproduces without it.
4. **Ruled out: general Tamil/Telugu/Kannada script shaping.** Every
   other construct in the same scripts — conjuncts, vowel signs,
   reordering, punctuation, mixed English runs — rendered correctly in
   the same fonts, same test run. The failure is specific to the
   native-digit Unicode block, not the script generally.
5. **Not ruled out / not further isolated in this pass**: whether this
   is a MuPDF C-library bug specific to *variable* fonts (all four
   downloaded fonts are variable TTFs) for these particular
   Unicode ranges, versus a bug that would also reproduce on a static
   (non-variable) build of the same fonts. This would be the next
   isolation step if native-digit rendering becomes a hard
   requirement (see "Follow-up" below) — not done here because a
   zero-cost mitigation already exists (next section).

**Classification: PyMuPDF** (specifically, its glyph-selection step
during page-content-stream generation for these codepoint ranges in
these fonts) — not font, not font embedding, not shaping/HarfBuzz, not
HTML/CSS, not text extraction, not Unicode normalization, not
bounding-box sizing. Devanagari's native digits, tested in the same
run with the same pipeline, rendered correctly — so this is not a
blanket "PyMuPDF can't do Indic digits" finding, it's specific to
these three scripts' fonts.

## MITIGATION (no architecture change required)

Render Telugu/Tamil/Kannada numerals using **Western Arabic digits
(0-9)**, not native-script digit codepoints. This is not a workaround
of convenience — Western digits are already the dominant convention in
modern printed Telugu/Tamil/Kannada text for exactly this kind of
content (prices, temperatures, dates), and this test's own "numerals"
case already mixed both forms (`₹500`, `37°C` in Western digits
rendered correctly in all four languages). The translation/rendering
pipeline should simply not convert Western digits to native-script
digit codepoints during localization, and should flag (not
auto-convert) any source content that already contains native
Telugu/Tamil/Kannada digit characters for that specific presentation
choice.

## BOUNDING-BOX / LAYOUT BEHAVIOR (all languages)

- `spare_height` was never `-1` (PyMuPDF's own "failed to fit" signal)
  across all 24 cases — nothing clipped even with deliberately tight
  rect heights.
- `scale` was `1.0` in every case (with `scale_low=1.0`, meaning no
  forced shrinking was needed or permitted) — the chosen rect heights
  were adequately sized for the given font-size/content combination in
  every test.
- Paragraph wrapping broke at word boundaries correctly in all four
  languages — no mid-syllable or mid-conjunct line breaks observed.
- Mixed-script (English+Indic) text shared a single line/box correctly
  in all four languages with no visible baseline or spacing glitch at
  the script boundary.

## OVERALL CLASSIFICATION

| Language | Classification |
|---|---|
| Hindi (Devanagari) | **PASS** |
| Telugu | **PASS WITH LIMITATIONS** (native digits only; Western-digit mitigation available) |
| Tamil | **PASS WITH LIMITATIONS** (native digits only; Western-digit mitigation available) |
| Kannada | **PASS WITH LIMITATIONS** (native digits only; Western-digit mitigation available) |

## GO/NO-GO DECISION

**GO.** The core question this experiment exists to answer — can
PyMuPDF + `insert_htmlbox` + Noto fonts correctly shape Indic
script text (conjuncts, reordering, ligatures) and behave predictably
for bounding-box fitting — is answered **yes** for all four target
languages. The one failure found is narrow, fully isolated to a
specific Unicode sub-range, does not indicate a fundamental rendering
problem, and has a practical, low-cost mitigation that doesn't require
a different rendering library or architecture change. Decision 7 in
`docs/research/ARCHITECTURE_DECISIONS.md` is updated (not reversed) to
record this finding and mitigation. Milestone 2's Document Model work
may proceed, per the instruction that governs this experiment — but
note the top-level instruction for this task capped scope at this
proof-of-concept; Document Model implementation itself was not started
in this pass.

## FOLLOW-UP (not required to proceed, worth tracking)

- If native-script digit rendering ever becomes a hard requirement
  (e.g. a user explicitly wants ౧౨౩ style output), isolate further:
  test a static (non-variable) instance of the same Noto fonts to
  determine if the bug is specific to variable-font parsing in this
  PyMuPDF version, and/or file an issue against PyMuPDF with this
  isolated repro if it's not already known.
- This proof did not test: RTL scripts (out of MVP scope per master
  plan Section 41), Malayalam (separately flagged as an OCR gap, not
  yet tested for rendering), font-weight/bold-italic variants via
  `insert_htmlbox`, or very long documents/many pages (performance).
