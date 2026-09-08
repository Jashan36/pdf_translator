# Local PDF Language Converter --- Technical Master Plan

**Project status:** Planning / architecture\
**Primary interface:** Streamlit\
**Primary runtime:** Local-first Python application\
**Primary goal:** Translate the textual content of an existing PDF into
a selected language while preserving the original document's visual
identity, layout, images, logos, colors, typography, and geometry as
closely as technically possible.

> **Core principle:** This is not a "PDF-to-text translator". It is a
> **document localization and visual-preservation system**. AI is
> responsible for language and semantic decisions; deterministic PDF
> software is responsible for geometry, rendering, and preservation.

------------------------------------------------------------------------

## 1. Executive Summary

The system accepts an English (or other source-language) PDF,
detects/infers the source language, lets the user select a target
language, translates the document with context, and produces a new PDF
that keeps the original design.

The first version is intended for personal and family use. It should
therefore prioritize:

1.  Privacy.
2.  Simplicity.
3.  Local execution.
4.  High visual fidelity.
5.  Support for Indian languages.
6.  No dependency on a ChatGPT/Claude/Gemini consumer subscription.
7.  Replaceable translation backends.
8.  Deterministic PDF reconstruction.
9.  Human review for difficult documents.
10. Clear failure reporting instead of pretending that every PDF can be
    reproduced perfectly.

### Target user flow

``` text
Upload PDF
    ↓
Analyze PDF
    ↓
Detect source language
    ↓
Select target language
    ↓
Build document context
    ↓
Translate semantic text units
    ↓
Fit translated text into original geometry
    ↓
Render reconstructed PDF
    ↓
Visual + semantic QA
    ↓
Preview
    ↓
Download translated PDF
```

------------------------------------------------------------------------

# 2. Non-Negotiable Requirements

## 2.1 Preservation requirements

The system should preserve, wherever the source PDF permits it:

-   page size
-   page count
-   page orientation
-   page background
-   images
-   photographs
-   logos
-   vector graphics
-   shapes
-   lines
-   colors
-   transparency
-   margins
-   text positions
-   text alignment
-   font size
-   font weight
-   italic state
-   text color
-   text rotation
-   headers
-   footers
-   page numbers
-   tables
-   hyperlinks where possible
-   overall visual hierarchy

### Important limitation

"Preserve exactly" is not mathematically guaranteed for arbitrary
languages.

If an English string occupies width `W` and its translation requires
width `W' > W`, then at least one of the following must change:

-   font size,
-   line wrapping,
-   line count,
-   bounding-box height,
-   tracking/spacing,
-   text box dimensions,
-   nearby object positions.

Therefore the actual requirement is:

> **Preserve all source geometry and visual properties unless language
> expansion makes the original geometry physically infeasible.**

The system must detect such cases rather than silently damaging the
page.

------------------------------------------------------------------------

# 3. What We Are Actually Building

The architecture should be separated into two fundamentally different
systems.

## A. Semantic system

Responsible for:

-   language detection
-   text extraction
-   reading order
-   document structure
-   contextual translation
-   terminology
-   glossary
-   consistency
-   translation confidence
-   human review

## B. Rendering system

Responsible for:

-   coordinates
-   bounding boxes
-   fonts
-   font size
-   font weight
-   color
-   images
-   logos
-   shapes
-   page geometry
-   text insertion
-   clipping
-   overflow
-   PDF generation

### Principle

``` text
AI answers:
"What should this text say?"

Deterministic software answers:
"Where and how should this text be rendered?"
```

Do not ask an LLM to recreate the entire PDF visually.

------------------------------------------------------------------------

# 4. Recommended Technology Stack

## 4.1 UI

### Streamlit

Use Streamlit for v1.

Reasons:

-   fast Python development
-   easy file upload
-   easy language selectors
-   progress indicators
-   previews
-   download buttons
-   no separate frontend required
-   ideal for local family use

Streamlit is the interface, not the document engine.

------------------------------------------------------------------------

## 4.2 Core PDF engine

### PyMuPDF

Primary choice for:

-   PDF opening
-   page inspection
-   text extraction
-   span-level metadata
-   bounding boxes
-   font information
-   color information
-   insertion of replacement text
-   rendering pages for QA

PyMuPDF's current `TextPage` span representation exposes text, bounding
boxes, font name, font size, font flags, color, opacity and other
geometry/style information.

Source: https://pymupdf.readthedocs.io/en/latest/textpage.html

### Why this matters

A span can be represented approximately as:

``` json
{
  "text": "Healthy food choices",
  "bbox": [72, 120, 280, 145],
  "font": "Helvetica-Bold",
  "size": 18,
  "flags": 16,
  "color": 0
}
```

This gives the rendering engine real geometry rather than asking an AI
model to guess.

------------------------------------------------------------------------

# 5. Document Understanding Layer

A PDF should first be converted into an internal representation.

Do NOT translate raw extracted text directly.

## Proposed document model

``` text
Document
 ├── metadata
 ├── source_language
 ├── target_language
 ├── pages[]
 │    ├── page_geometry
 │    ├── background
 │    ├── objects[]
 │    │    ├── text_block
 │    │    ├── image
 │    │    ├── vector
 │    │    ├── table
 │    │    └── unknown
 │    └── reading_order[]
 │
 ├── glossary
 ├── translation_memory
 └── QA_results
```

Each text object should retain:

``` text
id
page_number
reading_order
original_text
translated_text
bbox
font
font_size
font_flags
color
opacity
rotation
alignment
line_height
role
parent_block
section
confidence
translation_status
```

------------------------------------------------------------------------

# 6. Context Preservation

This is one of the most important components.

## Wrong approach

``` text
sentence → translator → translated sentence
```

This loses context.

## Correct approach

``` text
Document context
      ↓
Section context
      ↓
Paragraph context
      ↓
Current text block
      ↓
Sentence / span
```

The translation engine should receive enough context to understand
references, terminology and intent.

### Example

``` text
Previous:
"Iron is especially important during childhood."

Current:
"It supports healthy development."

Next:
"Children need adequate dietary iron."
```

The translation engine can now infer that "It" refers to iron.

------------------------------------------------------------------------

# 7. Context Package

For each translation unit, construct a controlled context package.

``` json
{
  "document_purpose": "Educational nutrition guide",
  "audience": "General Indian audience",
  "source_language": "English",
  "target_language": "Telugu",
  "tone": "Simple and informative",
  "section": "Nutrition",
  "previous_context": "...",
  "current_text": "It supports healthy development.",
  "following_context": "...",
  "glossary": {},
  "protected_terms": [],
  "layout_constraints": {
    "max_width": 240,
    "max_height": 60,
    "original_font_size": 18
  }
}
```

The model should return only the translation for the current semantic
unit, not a redesigned document.

------------------------------------------------------------------------

# 8. Translation Units

Do not translate individual PDF spans blindly.

Use a hierarchy:

``` text
Page
  ↓
Section
  ↓
Paragraph
  ↓
Sentence
  ↓
Span
```

### Preferred translation unit

Usually:

-   paragraph
-   heading
-   table cell
-   caption
-   list item

A span is primarily a **rendering unit**, not necessarily a semantic
unit.

This distinction is critical.

Example:

``` text
"Healthy " + "food " + "choices"
```

may be three PDF spans because "food" is bold, but semantically it is
one phrase.

Translate the semantic block first, then map the result back to the
visual spans.

------------------------------------------------------------------------

# 9. Protected Content

Some content must never be translated automatically.

Examples:

-   brand names
-   logos
-   URLs
-   email addresses
-   file names
-   product codes
-   serial numbers
-   legal identifiers
-   mathematical formulas
-   chemical formulas
-   programming code
-   ISBNs
-   citations
-   references where appropriate

Create a protected token system:

``` text
Original:
"Visit https://example.com for NUVISH products."

Internal:
"Visit __URL_001__ for __BRAND_001__ products."

Translate:
"__URL_001__ కోసం __BRAND_001__ ఉత్పత్తులను చూడండి."

Restore:
"Visit https://example.com ..."
```

------------------------------------------------------------------------

# 10. Translation Backends

The application must use a provider abstraction.

``` python
class TranslationProvider:
    def detect_language(self, text):
        ...

    def translate(self, segments, source, target, context=None):
        ...

    def supported_languages(self):
        ...
```

This prevents the project from becoming dependent on one vendor.

------------------------------------------------------------------------

## 10.1 Google Cloud Translation

Google Cloud Translation Advanced provides document translation for
formatted documents including PDF and DOCX and supports features such as
glossaries. Google's documentation states that PDF document translation
can preserve original formatting and layout, although this is a separate
capability from our own precise reconstruction engine.

Official documentation:
https://docs.cloud.google.com/translate/docs/advanced/translate-documents

Supported-format documentation:
https://docs.cloud.google.com/translate/docs/supported-formats

Pricing: https://cloud.google.com/products/translate/pricing

### Important

Do not assume Google Translate's web interface is equivalent to our
engine.

The consumer Google Translate document feature currently accepts PDF up
to 10 MB and 300 pages, but Google explicitly notes that text in
images/scanned PDF pages can appear in output without being translated.

Official help: https://support.google.com/translate/answer/2534559

Therefore:

**Google document translation can be a useful benchmark/backend, but it
should not replace our preservation pipeline.**

------------------------------------------------------------------------

# 11. Google Gemini API

Gemini can be used as an optional semantic/context translation backend.

Google's current Gemini API pricing page lists a free tier for selected
models and a paid tier with higher limits and access to additional
models. The current pricing page also identifies a Flash-Lite model as
optimized for translation and simple data processing.

Official pricing: https://ai.google.dev/gemini-api/docs/pricing

### Important privacy consideration

The current Google AI API pricing documentation states that content on
the free tier may be used to improve Google's products, whereas paid API
usage is listed as not used for product improvement.

For private family documents, this must be an explicit user choice.

------------------------------------------------------------------------

# 12. Local Translation Backends

## 12.1 Argos Translate

Argos Translate is an open-source offline Python translation library.

It can run locally and supports installed language packages.

Repository: https://github.com/argosopentech/argos-translate

Useful for:

-   offline mode
-   no external API
-   no API key
-   family/private documents
-   fallback translation

Limitation:

Translation quality is language-pair dependent and generally should not
be assumed equivalent to the strongest commercial models.

------------------------------------------------------------------------

## 12.2 LibreTranslate

LibreTranslate is an open-source, self-hostable translation API built on
Argos Translate.

Repository: https://github.com/LibreTranslate/LibreTranslate

Useful architecture:

``` text
Streamlit
   ↓
Local HTTP API
   ↓
LibreTranslate
   ↓
Argos Translate
```

This is optional because direct Argos integration is simpler for a
purely local application.

------------------------------------------------------------------------

# 13. NLLB

Meta's NLLB family supports more than 200 languages.

Hugging Face documentation:
https://huggingface.co/docs/transformers/main/model_doc/nllb

However, NLLB should NOT be treated as an automatic "best translator".

The NLLB model card explicitly states that the research model is not
intended for production deployment, domain-specific medical/legal text,
or document translation, and notes limitations on long inputs.

Example: https://huggingface.co/facebook/nllb-200-3.3B

Therefore:

**Use NLLB as an optional research/local translation backend, not as the
sole correctness authority.**

------------------------------------------------------------------------

# 14. Language Detection

Language detection should happen before translation.

Recommended strategy:

``` text
PDF text extraction
       ↓
sample multiple text blocks
       ↓
language detector
       ↓
confidence score
       ↓
user confirmation
```

Do not rely on one sentence.

For a multilingual document:

``` text
Page 1 → English
Page 2 → English
Page 3 → Telugu
Page 4 → English
```

the system should allow:

``` text
Document language:
[ Auto detect ]

Detected:
English — 96%

[Confirm]
```

For mixed-language PDFs, language detection should operate at block
level.

------------------------------------------------------------------------

# 15. OCR Strategy

There are two fundamentally different PDF classes.

## Class A --- Native text PDF

The PDF contains real text objects.

Use:

``` text
PyMuPDF
```

No OCR should be necessary.

This is the highest-fidelity path.

------------------------------------------------------------------------

## Class B --- Scanned PDF

The PDF contains page images.

Use OCR.

### Primary OCR candidate: PaddleOCR

PaddleOCR is an open-source OCR/document-AI toolkit that supports
document/image processing and many languages.

Repository: https://github.com/PaddlePaddle/PaddleOCR

It can provide text localization and recognition, which is important
because we need bounding boxes.

------------------------------------------------------------------------

## Alternative: docTR

docTR provides deep-learning OCR with text detection and recognition.

Repository: https://github.com/mindee/doctr

It supports PDF/image input and provides localized text recognition.

Apache-2.0 licensed.

------------------------------------------------------------------------

## Alternative: EasyOCR

EasyOCR supports several Indian-language scripts including Telugu,
Kannada, Tamil and Devanagari languages.

Repository: https://github.com/JaidedAI/EasyOCR

Useful for:

-   simple OCR fallback
-   Indian language OCR experiments

------------------------------------------------------------------------

# 16. Docling

Docling is useful for advanced document understanding.

It provides:

-   PDF parsing
-   layout understanding
-   reading order
-   table structures
-   metadata
-   OCR integration
-   structured document representation

Repository: https://github.com/docling-project/docling

License: MIT

Source: https://github.com/docling-project/docling/blob/main/LICENSE

### Important architectural decision

Do not make Docling responsible for final PDF rendering.

Use it as an optional **document understanding layer**.

Potential pipeline:

``` text
PDF
 ↓
PyMuPDF
 ↓
Docling for complex structure
 ↓
Internal Document Model
 ↓
Translation
 ↓
Our rendering engine
```

For simple PDFs, PyMuPDF alone should be sufficient.

------------------------------------------------------------------------

# 17. PDF Extraction Strategy

## First pass

Extract:

-   blocks
-   lines
-   spans
-   characters where necessary
-   images
-   page dimensions
-   links
-   annotations
-   fonts
-   colors

## Second pass

Classify objects:

``` text
TEXT
IMAGE
VECTOR
TABLE
FORM
ANNOTATION
UNKNOWN
```

## Third pass

Build semantic groups:

``` text
span → line → paragraph → section
```

------------------------------------------------------------------------

# 18. Bounding Box Model

Every text element should have a coordinate rectangle:

``` text
x0
y0
x1
y1
```

Width:

``` text
W = x1 - x0
```

Height:

``` text
H = y1 - y0
```

The original geometry must be stored before any modification.

------------------------------------------------------------------------

# 19. Text-Fit Algorithm

For each translated block:

### Step 1

Try original font size.

``` text
S = S_original
```

### Step 2

Measure translated text.

If:

``` text
required_width <= available_width
```

and

``` text
required_height <= available_height
```

then preserve the original size.

### Step 3

If it does not fit:

Reduce font size within a defined tolerance.

For example:

``` text
S_original = 18 pt
minimum = 15 pt
```

Search:

``` text
18
17.5
17
16.5
...
15
```

### Step 4

If still impossible:

Allow controlled wrapping.

### Step 5

If still impossible:

Mark:

``` text
LAYOUT_WARNING
```

and ask for review.

------------------------------------------------------------------------

# 20. Mathematical Layout Objective

Define the original style state:

``` text
O = {x, y, w, h, font, size, weight, color, rotation}
```

Define translated rendering state:

``` text
T = {x', y', w', h', font', size', weight', color', rotation'}
```

We want to minimize:

``` text
E = λg Eg + λs Es + λf Ef + λc Ec
```

where:

-   `Eg` = geometry deviation
-   `Es` = style deviation
-   `Ef` = font-size deviation
-   `Ec` = color/style deviation
-   `λ` values are configurable weights

Subject to:

``` text
text is readable
text is not clipped
text does not overlap protected objects
text remains inside its intended region
```

This gives the renderer a measurable objective rather than a vague
instruction such as "make it look similar."

------------------------------------------------------------------------

# 21. Style Preservation

Store:

``` text
font family
font size
font flags
bold
italic
color
opacity
alignment
rotation
line spacing
```

PyMuPDF exposes font and span properties including font name, size,
flags, color, opacity and bounding box.

However, font metadata is not always perfect. PDF font programs can
contain incorrect or incomplete flags.

Therefore:

``` text
PDF metadata
      +
visual inspection
      +
fallback heuristics
```

may be necessary.

------------------------------------------------------------------------

# 22. Target-Language Font System

This is mandatory for Indian languages.

The original font may not contain Telugu/Hindi/Kannada/Tamil glyphs.

Therefore the system needs a language-aware fallback table.

Example:

``` yaml
te:
  primary: "Noto Sans Telugu"
  fallback:
    - "Noto Serif Telugu"

hi:
  primary: "Noto Sans Devanagari"
  fallback:
    - "Noto Serif Devanagari"

ta:
  primary: "Noto Sans Tamil"
  fallback:
    - "Noto Serif Tamil"

kn:
  primary: "Noto Sans Kannada"
  fallback:
    - "Noto Serif Kannada"
```

The visual style should remain as close as possible to the original:

``` text
Original:
Helvetica Bold

Target:
Noto Sans Telugu Bold
```

Do not attempt to force an English-only font to render an unsupported
script.

------------------------------------------------------------------------

# 23. Image and Logo Preservation

Images and logos should normally be copied from the original PDF.

Do NOT:

-   regenerate logos
-   ask an image model to recreate logos
-   OCR text inside logos unless necessary
-   redraw photographs

The safest path is:

``` text
Original image object
        ↓
copy unchanged
        ↓
translated PDF
```

If an image contains text that must be translated, treat it as a
separate OCR/image-localization problem.

------------------------------------------------------------------------

# 24. Text Inside Images

This is a separate feature and should not be part of MVP.

Example:

``` text
[IMAGE]
  "SALE 50% OFF"
```

The PDF itself may contain no text object.

Required pipeline:

``` text
image
 ↓
OCR
 ↓
text region
 ↓
translation
 ↓
background reconstruction
 ↓
translated text rendering
 ↓
image replacement
```

This is significantly harder than normal PDF text replacement.

------------------------------------------------------------------------

# 25. Tables

Tables require semantic grouping.

Do not treat every table cell as an independent random rectangle.

Represent:

``` text
Table
 ├── Row
 │    ├── Cell
 │    ├── Cell
 │    └── Cell
 ├── Row
 └── Row
```

Translate cell contents while preserving:

-   borders
-   cell background
-   alignment
-   column widths
-   row heights
-   numerical formatting

If text expansion causes a row to overflow, attempt:

1.  wrapping
2.  font reduction
3.  controlled row-height expansion
4.  warning

------------------------------------------------------------------------

# 26. Headers and Footers

Detect repeated blocks across pages.

If the same text appears at approximately the same coordinates on many
pages, classify it as:

``` text
HEADER
```

or:

``` text
FOOTER
```

Translate once, then apply consistently.

This prevents inconsistent translations across pages.

------------------------------------------------------------------------

# 27. Translation Memory

Maintain a local translation memory:

``` json
{
  "source": "Nutritional value",
  "target_language": "te",
  "translation": "...",
  "approved": true
}
```

If the same phrase appears 50 times, it should normally receive the same
approved translation.

This improves consistency.

------------------------------------------------------------------------

# 28. Glossary

Allow users to define:

``` yaml
glossary:
  protein:
    te: "..."
  calorie:
    te: "..."
  serving:
    te: "..."
```

Glossary precedence:

``` text
protected terms
    >
approved glossary
    >
translation memory
    >
translation model
```

------------------------------------------------------------------------

# 29. Translation Quality Modes

## Mode 1 --- Standard

Use:

-   Google translation backend
-   local translation backend
-   or another inexpensive provider

Best for ordinary documents.

## Mode 2 --- Contextual

Use an LLM-capable backend.

Provide:

-   section context
-   paragraph context
-   glossary
-   terminology
-   target audience
-   tone
-   layout constraints

## Mode 3 --- Private / Offline

Use:

-   local OCR
-   local translation
-   local rendering

No external document upload.

------------------------------------------------------------------------

# 30. Provider Abstraction

Suggested interface:

``` python
class TranslationProvider(Protocol):

    def detect_language(
        self,
        text: str
    ) -> DetectionResult:
        ...

    def translate(
        self,
        segments: list[TranslationSegment],
        source_language: str,
        target_language: str,
        context: TranslationContext
    ) -> list[TranslationResult]:
        ...

    def supported_languages(self) -> list[Language]:
        ...
```

Implementations:

``` text
GoogleTranslationProvider
GeminiProvider
ArgosProvider
NLLBProvider
LibreTranslateProvider
```

The UI should not know which provider is being used.

------------------------------------------------------------------------

# 31. Provider Selection

Recommended fallback:

``` text
User selects:
"Standard"

        ↓

Google / configured provider

        ↓

if unavailable

        ↓

Local fallback
```

For private mode:

``` text
Local provider only
```

For contextual mode:

``` text
LLM provider
+
deterministic renderer
```

------------------------------------------------------------------------

# 32. Why We Should Not Depend on ChatGPT/Claude Consumer Plans

A user's ChatGPT Plus/Pro or Claude subscription should NOT be required.

Consumer subscriptions and developer APIs are separate architectural
concerns.

Our application should own the translation-provider configuration.

This means:

``` text
User has ChatGPT subscription
       ≠
our application automatically has API access
```

If we later integrate a paid API, the application must use the
provider's developer/API credentials according to its terms.

------------------------------------------------------------------------

# 33. Free-Only Operation

A family member with no AI subscription should still be able to use:

``` text
Streamlit
+
PyMuPDF
+
local OCR
+
Argos/NLLB/local translation
+
local fonts
+
local renderer
```

No consumer AI account is required.

The trade-off is translation quality, speed and hardware requirements.

------------------------------------------------------------------------

# 34. Privacy Architecture

Default:

``` text
Local PDF
     ↓
Local processing
```

No upload.

If cloud translation is enabled:

``` text
PDF
 ↓
extract only required text
 ↓
send text segments
 ↓
receive translation
 ↓
local reconstruction
```

Do NOT upload the entire PDF when the translation provider only needs
text.

This also protects:

-   logos
-   images
-   personal photos
-   metadata
-   unrelated page content

------------------------------------------------------------------------

# 35. Metadata Privacy

PDFs can contain:

-   author
-   creator
-   producer
-   creation date
-   modification date
-   embedded thumbnails
-   XMP metadata
-   hidden objects

The application should offer:

``` text
☑ Preserve metadata
☐ Remove personal metadata
```

Default for family privacy:

**Preserve only when explicitly requested.**

------------------------------------------------------------------------

# 36. Visual QA

Visual QA is mandatory.

After generating the translated PDF:

``` text
Original page
       ↓
render PNG

Translated page
       ↓
render PNG

      ↓

compare
```

Generate:

1.  side-by-side preview
2.  optional overlay
3.  difference heatmap
4.  text overflow warnings

------------------------------------------------------------------------

# 37. Visual Comparison Metrics

For page images:

``` text
I_original
I_translated
```

Compute image difference:

``` text
D = |I_original - I_translated|
```

But do NOT interpret every difference as an error.

Translated text is expected to differ.

Therefore create region masks:

``` text
protected visual regions
translated text regions
```

Then evaluate separately.

### Protected regions

Differences should be near zero.

Examples:

-   logo
-   photograph
-   background
-   decorative shapes

### Text regions

Differences are expected.

Evaluate:

-   position
-   clipping
-   overflow
-   style
-   color
-   baseline
-   font-size deviation

------------------------------------------------------------------------

# 38. Semantic QA

After translation, validate:

-   number preservation
-   dates
-   URLs
-   percentages
-   currency
-   units
-   named entities
-   protected terms
-   table row/column counts
-   untranslated text
-   missing text

Example:

``` text
Original:
Vitamin D: 600 IU

Translated:
Vitamin D: 600 IU

PASS
```

If:

``` text
Vitamin D: 600 IU

→

Vitamin D: 60 IU
```

the system should flag it.

------------------------------------------------------------------------

# 39. Numerical Consistency

Numbers should be extracted before translation.

For each block:

``` text
numbers_original = [...]
numbers_translated = [...]
```

Compare normalized values.

The following must normally remain invariant:

-   100
-   25%
-   ₹500
-   37°C
-   10 mg
-   2.5 L
-   dates
-   URLs

Localized formatting can change separators, but numerical meaning must
not silently change.

------------------------------------------------------------------------

# 40. Page-Level Confidence

Each page receives:

``` text
layout_score
translation_score
ocr_score
semantic_score
```

Example:

``` text
Page 1
OCR:          0.99
Translation:  0.94
Layout:       0.98
Semantic QA:  1.00

Overall:      0.97
```

These are engineering diagnostics, not claims of human-level
correctness.

------------------------------------------------------------------------

# 41. MVP Scope

The first version should NOT try to solve everything.

## MVP supports

-   native text PDFs
-   English source
-   Telugu/Hindi/Tamil/Kannada first
-   paragraph text
-   headings
-   lists
-   basic tables
-   images
-   logos
-   colors
-   font size
-   bold/italic
-   bounding boxes
-   language detection
-   Google/local translation backend
-   side-by-side preview
-   PDF export

## MVP does not guarantee

-   scanned PDFs
-   handwritten documents
-   text inside images
-   complicated forms
-   arbitrary RTL documents
-   complex vector text
-   perfect typography
-   100% layout identity

------------------------------------------------------------------------

# 42. Phase 1 --- PDF Forensics

Build:

``` text
upload PDF
 ↓
analyze
 ↓
display:
 pages
 text blocks
 fonts
 sizes
 colors
 bounding boxes
 images
```

No translation yet.

### Deliverable

A JSON representation:

``` json
{
  "pages": [
    {
      "page": 1,
      "width": 595.28,
      "height": 841.89,
      "objects": []
    }
  ]
}
```

### Success criterion

The extracted document model must explain the original PDF sufficiently
to reconstruct a visually similar copy.

------------------------------------------------------------------------

# 43. Phase 2 --- Exact Text Replacement

Use a manually supplied translation.

``` text
Original PDF
 ↓
replace English text
 ↓
same PDF layout
```

No AI.

### Why?

This isolates PDF engineering from translation quality.

If this fails, adding AI will only make debugging harder.

------------------------------------------------------------------------

# 44. Phase 3 --- Automatic Text-Fit Engine

Implement:

``` text
preserve size
 ↓
measure
 ↓
fit?
 ├── yes → render
 └── no
      ↓
   reduce size
      ↓
   fit?
      ├── yes → render
      └── no → wrap
```

Then add overflow detection.

------------------------------------------------------------------------

# 45. Phase 4 --- Language Detection

Implement automatic detection at:

-   document level
-   page level
-   block level where required

Show confidence and allow manual override.

------------------------------------------------------------------------

# 46. Phase 5 --- Translation Provider

Start with one provider.

Recommended first experiment:

``` text
Google Cloud Translation
```

because Google provides a document translation API and direct PDF
support.

Then add:

``` text
Argos
```

for offline fallback.

Then optionally:

``` text
Gemini
```

for contextual translation.

------------------------------------------------------------------------

# 47. Phase 6 --- Context Engine

Implement:

``` text
document summary
section summary
paragraph context
current block
next block
glossary
protected terms
```

Do not send the entire PDF to an LLM for every sentence.

That is wasteful and can increase inconsistency.

------------------------------------------------------------------------

# 48. Phase 7 --- OCR

Only after native-text PDFs work.

Pipeline:

``` text
detect native text
       │
       ├── yes → PyMuPDF
       │
       └── no → OCR
                    ↓
               PaddleOCR
                    ↓
              bounding boxes
                    ↓
              translation
                    ↓
               rendering
```

------------------------------------------------------------------------

# 49. Phase 8 --- Tables and Complex Layout

Add:

-   table detection
-   cell grouping
-   merged cells
-   repeated headers
-   multi-column reading order
-   captions
-   footnotes

Use Docling as an optional structural analyzer for difficult PDFs.

------------------------------------------------------------------------

# 50. Phase 9 --- Visual QA

Implement:

``` text
original render
       +
translated render
       ↓
comparison
       ↓
warnings
```

Warnings:

``` text
⚠ Text overflow
⚠ Font reduced from 18pt to 15pt
⚠ Missing target glyph
⚠ OCR confidence low
⚠ Image text detected
⚠ Possible numerical mismatch
```

------------------------------------------------------------------------

# 51. Phase 10 --- Family-Friendly UI

Final interface:

``` text
PDF LOCALIZER
────────────────────────────

Upload PDF
[ Choose file ]

Detected language:
English (96%)

Translate to:
[ Telugu ▼ ]

Quality:
○ Standard
● Contextual
○ Private / Offline

Preserve:
☑ Layout
☑ Images
☑ Logos
☑ Colors
☑ Typography

[ Translate ]

────────────────────────────

Preview
[ Original ] [ Translated ]

Warnings: 1

[ Download PDF ]
```

The family member should not need to understand any technical component.

------------------------------------------------------------------------

# 52. Suggested Project Structure

``` text
local-pdf-localizer/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
│
├── config/
│   ├── languages.yaml
│   ├── fonts.yaml
│   └── providers.yaml
│
├── core/
│   ├── models.py
│   ├── pipeline.py
│   │
│   ├── pdf/
│   │   ├── analyzer.py
│   │   ├── extractor.py
│   │   ├── renderer.py
│   │   ├── fonts.py
│   │   └── images.py
│   │
│   ├── document/
│   │   ├── structure.py
│   │   ├── grouping.py
│   │   ├── reading_order.py
│   │   └── language.py
│   │
│   ├── translation/
│   │   ├── base.py
│   │   ├── google.py
│   │   ├── gemini.py
│   │   ├── argos.py
│   │   └── nllb.py
│   │
│   ├── context/
│   │   ├── builder.py
│   │   ├── glossary.py
│   │   └── memory.py
│   │
│   ├── ocr/
│   │   ├── detector.py
│   │   ├── paddle.py
│   │   └── doctr.py
│   │
│   ├── layout/
│   │   ├── fit.py
│   │   ├── wrapping.py
│   │   ├── collision.py
│   │   └── scoring.py
│   │
│   └── qa/
│       ├── semantic.py
│       ├── visual.py
│       └── report.py
│
├── fonts/
│   ├── telugu/
│   ├── devanagari/
│   ├── tamil/
│   └── kannada/
│
├── tests/
│   ├── fixtures/
│   ├── test_extraction.py
│   ├── test_layout.py
│   ├── test_translation.py
│   └── test_qa.py
│
└── outputs/
```

------------------------------------------------------------------------

# 53. Recommended Development Order

Do NOT build all features simultaneously.

## Milestone 1

``` text
PDF → inspect → JSON
```

## Milestone 2

``` text
PDF → replace text → PDF
```

## Milestone 3

``` text
PDF → translated text → preserve geometry
```

## Milestone 4

``` text
PDF → language detection → translation → PDF
```

## Milestone 5

``` text
PDF → context-aware translation → PDF
```

## Milestone 6

``` text
scanned PDF → OCR → translation → PDF
```

## Milestone 7

``` text
complex PDF → structural analysis → translation → reconstruction
```

## Milestone 8

``` text
visual QA + semantic QA + family UI
```

------------------------------------------------------------------------

# 54. Test Corpus

Before trusting the system, create a fixed test set.

## Test PDF A

Simple one-page text document.

## Test PDF B

Branding-heavy brochure.

## Test PDF C

Two-column document.

## Test PDF D

Table-heavy document.

## Test PDF E

Image-heavy document.

## Test PDF F

Scanned PDF.

## Test PDF G

English → Telugu.

## Test PDF H

English → Hindi.

## Test PDF I

English → Tamil.

## Test PDF J

English → Kannada.

For every test:

``` text
original.pdf
translated.pdf
visual_report.json
semantic_report.json
```

------------------------------------------------------------------------

# 55. Golden Test Principle

Never judge the project only by:

> "It looks okay."

Create objective regression tests.

For example:

``` text
logo position deviation < 1 pt
image geometry deviation = 0
page dimensions deviation = 0
text clipping = 0
protected-object overlap = 0
```

Translation itself cannot be reduced to a single perfect numeric metric,
so human review remains necessary for high-value documents.

------------------------------------------------------------------------

# 56. Failure Handling

The system must never silently produce a damaged PDF.

If a block cannot fit:

``` text
ERROR/WARNING:
Page 4
Block 12
Original: 18 pt
Minimum allowed: 14 pt
Required size: 11.5 pt

Action:
[Review]
```

The user can then choose:

``` text
Keep smaller text
Allow wrapping
Edit translation
Skip translation
```

------------------------------------------------------------------------

# 57. What "Preserve Layout" Means

The system should define preservation explicitly.

### Level 0

Only translate text.

### Level 1

Preserve page size and images.

### Level 2

Preserve text coordinates and styles.

### Level 3

Preserve layout with adaptive text fitting.

### Level 4

Preserve layout + tables + complex reading order.

### Level 5

Preserve image-embedded text and complex scanned layouts.

MVP target:

**Level 3.**

------------------------------------------------------------------------

# 58. Important Technical Reality

There is no universal algorithm that can take every arbitrary PDF in
every language and guarantee pixel-identical output after translation.

Reasons include:

1.  Different scripts have different glyph metrics.
2.  Some languages expand substantially.
3.  Some scripts have different line-breaking rules.
4.  Some fonts have no equivalent target-script family.
5.  PDF files may contain text as vector outlines or images.
6.  Scanned documents have no original text geometry.
7.  Text inside images requires image reconstruction.
8.  RTL scripts require different layout behavior.
9.  PDF font metadata can be incomplete.
10. Complex PDFs can contain proprietary or unusual structures.

Therefore the project should optimize for **controlled fidelity**, not
claim impossible universality.

------------------------------------------------------------------------

# 59. Security

For local use:

-   process temporary files in a controlled directory
-   delete temporary files after job completion
-   do not log document contents by default
-   do not log API payloads
-   store API keys in environment variables
-   never hard-code keys
-   sanitize filenames
-   restrict upload size
-   validate PDF files
-   prevent path traversal
-   optionally encrypt local translation memory

------------------------------------------------------------------------

# 60. Cloud Deployment --- Later

Do not deploy the first version to Vercel.

For a local family tool:

``` text
localhost
```

is simpler and more private.

If cloud deployment becomes necessary later:

``` text
Frontend
  ↓
Web application
  ↓
Python processing worker
  ↓
Object storage
  ↓
Translation provider
```

The heavy PDF/OCR processing should not be assumed to fit comfortably
into a serverless frontend runtime.

------------------------------------------------------------------------

# 61. Why Local-First Is the Correct V1

Advantages:

-   private
-   no recurring hosting cost
-   no upload limits imposed by a web service
-   easier debugging
-   direct access to local fonts/models
-   easy family deployment
-   works without consumer AI subscriptions
-   can operate offline

Disadvantages:

-   installation is more difficult
-   model downloads can be large
-   local inference may be slow
-   hardware differences matter

For this project's intended audience, privacy and simplicity outweigh
remote infrastructure.

------------------------------------------------------------------------

# 62. Translation Backend Decision

Recommended initial configuration:

``` text
DEFAULT:
Google Cloud Translation / configured provider

OFFLINE:
Argos Translate

OPTIONAL LOCAL RESEARCH:
NLLB

CONTEXTUAL:
Gemini API or another LLM API

OCR:
PaddleOCR

PDF:
PyMuPDF

STRUCTURAL FALLBACK:
Docling

UI:
Streamlit
```

This is a modular architecture, not a commitment to every dependency.

------------------------------------------------------------------------

# 63. Dependency Principle

Do not install every library on day one.

Start with:

``` text
streamlit
pymupdf
```

Then add:

``` text
translation provider
```

Then:

``` text
language detection
```

Then:

``` text
OCR
```

Then:

``` text
Docling
```

This prevents dependency bloat and makes debugging tractable.

------------------------------------------------------------------------

# 64. Proposed V1 Stack

### Required

-   Python
-   Streamlit
-   PyMuPDF
-   Pydantic/dataclasses for internal models
-   one translation provider
-   Unicode target fonts

### Optional

-   Argos Translate
-   PaddleOCR
-   Docling
-   Gemini API
-   Google Cloud Translation
-   EasyOCR
-   docTR

------------------------------------------------------------------------

# 65. Acceptance Criteria

The MVP is complete when:

### Input

A native text PDF can be uploaded.

### Detection

The source language can be detected or manually selected.

### Translation

A target language can be selected.

### Preservation

The system preserves:

-   page dimensions
-   images
-   logos
-   colors
-   basic shapes
-   text positions
-   text alignment
-   font styling
-   approximate font size

### Adaptation

The system can handle moderate text expansion.

### QA

The system identifies:

-   clipping
-   overflow
-   missing text
-   numerical mismatches
-   unsupported glyphs

### Output

A valid PDF is produced.

### Privacy

Local mode does not send the PDF outside the machine.

------------------------------------------------------------------------

# 66. Future Features

After MVP:

-   OCR
-   scanned PDF support
-   image text translation
-   RTL languages
-   multilingual documents
-   table reconstruction
-   translation memory
-   glossary editor
-   batch translation
-   multiple target languages
-   editable translations
-   visual diff
-   automatic quality scoring
-   local LLM context engine
-   desktop packaging
-   Android wrapper
-   optional cloud deployment

------------------------------------------------------------------------

# 67. Engineering Rules

These rules should govern the project.

## Rule 1

**Never use an LLM to guess PDF geometry when deterministic geometry is
available.**

## Rule 2

**Never translate a document as one giant string.**

## Rule 3

**Never translate individual visual spans without semantic grouping.**

## Rule 4

**Never regenerate images/logos unless image-text localization is
explicitly requested.**

## Rule 5

**Never silently shrink text until it becomes unreadable.**

## Rule 6

**Never assume an English font supports the target script.**

## Rule 7

**Never claim 100% visual identity for arbitrary PDFs.**

## Rule 8

**Never make the entire system dependent on one AI provider.**

## Rule 9

**Separate semantic intelligence from deterministic rendering.**

## Rule 10

**When uncertain, produce a warning instead of inventing a result.**

------------------------------------------------------------------------

# 68. Final Architecture

``` text
                         ┌─────────────────────┐
                         │      Streamlit      │
                         │        UI           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Pipeline Manager  │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
       │ PDF Analyzer│      │ Context      │      │ Translation │
       │             │      │ Engine       │      │ Providers   │
       └──────┬──────┘      └──────┬───────┘      └──────┬──────┘
              │                    │                     │
              ▼                    ▼                     ▼
       ┌────────────────────────────────────────────────────────┐
       │              Internal Document Model                  │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │   Layout Engine     │
                         │                     │
                         │ bbox preservation   │
                         │ font fitting        │
                         │ wrapping            │
                         │ collision detection │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   PDF Renderer      │
                         │     PyMuPDF         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     QA Engine       │
                         │                     │
                         │ visual QA           │
                         │ semantic QA         │
                         │ numerical QA        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              FINAL PDF
```

------------------------------------------------------------------------

# 69. Recommended First Build

Do not begin with translation.

Build this first:

``` text
Upload PDF
   ↓
Analyze PDF
   ↓
Show:
  page count
  page size
  text blocks
  bounding boxes
  fonts
  font sizes
  colors
  images
   ↓
Render an extracted/reconstructed preview
```

Then prove:

> **Can our system understand the visual structure of the original PDF
> before we attempt to translate it?**

Once that is proven, translation becomes a separate layer.

------------------------------------------------------------------------

# 70. Definition of Success

The project is successful when a family member can take:

``` text
English branded PDF
```

and produce:

``` text
Telugu/Hindi/Tamil/Kannada PDF
```

without needing to understand AI, while the resulting document retains
the original visual identity as closely as technically possible.

The deepest architectural principle is:

``` text
             MEANING
                │
             AI layer
                │
                ▼
           TRANSLATED TEXT
                │
        deterministic layer
                │
                ▼
             GEOMETRY
                │
                ▼
             PDF
```

**AI should change the language, not the design.**

------------------------------------------------------------------------

# 71. Verified Research Sources

The following sources were checked while preparing this plan.

### PyMuPDF

-   TextPage and span geometry/style documentation:
    https://pymupdf.readthedocs.io/en/latest/textpage.html

### Google Cloud Translation

-   Document translation:
    https://docs.cloud.google.com/translate/docs/advanced/translate-documents
-   Supported formats:
    https://docs.cloud.google.com/translate/docs/supported-formats
-   Pricing: https://cloud.google.com/products/translate/pricing
-   Google Translate consumer document translation:
    https://support.google.com/translate/answer/2534559

### Google Gemini API

-   Current Gemini API pricing/free-tier information:
    https://ai.google.dev/gemini-api/docs/pricing

### Docling

-   Project: https://github.com/docling-project/docling
-   License:
    https://github.com/docling-project/docling/blob/main/LICENSE

### PaddleOCR

-   Project: https://github.com/PaddlePaddle/PaddleOCR

### docTR

-   Project: https://github.com/mindee/doctr

### EasyOCR

-   Project: https://github.com/JaidedAI/EasyOCR

### Argos Translate

-   Project: https://github.com/argosopentech/argos-translate

### LibreTranslate

-   Project: https://github.com/LibreTranslate/LibreTranslate

### NLLB

-   Hugging Face documentation:
    https://huggingface.co/docs/transformers/main/model_doc/nllb
-   NLLB-200 model card: https://huggingface.co/facebook/nllb-200-3.3B

------------------------------------------------------------------------

# 72. Technical Lead Decision

For V1, the project should be built as:

``` text
Python
+
Streamlit
+
PyMuPDF
+
Internal Document Model
+
One translation provider
+
Unicode target fonts
+
Layout/Fit Engine
+
Visual QA
```

Then expand to:

``` text
             V1
              │
              ▼
       Native text PDFs
              │
              ▼
        OCR/scanned PDFs
              │
              ▼
        Complex documents
              │
              ▼
       Image-text localization
```

The project should **earn complexity only when the previous layer is
proven**.

This is the safest path to a reliable personal/family PDF localization
system.
