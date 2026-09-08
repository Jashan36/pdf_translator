# PDF Localizer — Claude Code Rules

Full architecture and rationale: [local_pdf_localizer_technical_master_plan.md](local_pdf_localizer_technical_master_plan.md).
Current status and next steps: [PROJECT_STATE.md](PROJECT_STATE.md) — read it before touching code.

## Primary objective

Build a local-first PDF translation/localization system that preserves
the original document's visual identity as closely as technically
possible.

## Core principle

AI changes language. Deterministic software preserves the document.
Never ask an LLM to guess PDF geometry, coordinates, or rendering —
that is PyMuPDF's job, not the model's.

## Research rule

Never implement an unfamiliar API, library, or model from memory.
Verify against current official documentation (WebFetch/WebSearch),
the official GitHub repository, and — for models — the model card,
before writing code against it. If official docs and prior knowledge
disagree, trust the current official docs. Use the
`technical-research` skill for anything non-trivial.

## Dependency rule

Never invent package names, APIs, model identifiers, CLI flags, MCP
tool names, or config parameters. Before adding a dependency, verify:
package name, version, official repository, license, Python
compatibility, and installation method. Use the
`dependency-verification` skill and record the result in
`docs/dependencies.md`.

## Architecture rule

Keep these layers separate and do not let one leak into another:

```text
PDF extraction → Document model → OCR → Context → Translation
→ Layout/fit → Rendering → QA
```

Semantic decisions (what text should say) belong to the translation
layer. Geometry/rendering decisions belong to deterministic PDF code.
See Section 3 of the master plan.

## Translation rule

IndicTrans2 is the primary candidate for Indic-language translation
quality once we get past the pluggable-provider MVP stage (Section 10
of the master plan covers the provider abstraction). A local LLM
(Ollama/Qwen or similar) is for contextual reasoning and post-editing
review, never for PDF rendering or geometry decisions. Never guess an
IndicTrans2 (or any translator's) language code — verify against the
current official repository.

## Privacy

No document leaves the local machine unless the user explicitly
enables an external provider for that run. Default mode is fully
local (Section 34).

## Development protocol

Before changing code:

1. Read `PROJECT_STATE.md`.
2. Inspect the existing implementation relevant to the change.
3. Identify the current milestone (Section 53 of the master plan).
4. Research unfamiliar APIs (`technical-research` skill).
5. Make the minimal change needed for that milestone — do not jump
   ahead to a later milestone's features (Section 72: "earn
   complexity only when the previous layer is proven").
6. Run tests (`pytest tests/`).
7. Verify the output (run the app, or a targeted script) — don't just
   trust that code "looks right".
8. Update `PROJECT_STATE.md`.

## PDF rule

Never assume visual appearance represents PDF structure. Inspect the
actual PDF internals (`pdf-forensics` skill) — text may be native,
OCR'd, vector outlines, or raster images, and font metadata can be
incomplete or wrong.

## QA rule

A translated PDF is not "done" until it passes structural QA (Section
39: numbers/dates/URLs/units unchanged) and visual QA (Section 36-37:
protected regions near-zero diff, text regions checked for
clipping/overflow). Use the `visual-pdf-qa` skill.

## Stop rule

If a requirement is ambiguous, or implementing it would require
guessing (an unverified API, an undecided architecture choice, a
product decision only the user can make), stop and either research it
first or ask — do not invent a plausible-sounding answer.

## Working directory rule

Work only inside this repository. Do not read, write, or execute
anything outside the project root or its git worktree.
