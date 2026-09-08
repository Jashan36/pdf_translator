---
name: technical-research
description: Verification-first research protocol for any library, API, model, or tool this project doesn't already have working code for — check official docs/repo/license/version before writing code against it. Use before implementing anything involving PyMuPDF, PaddleOCR, IndicTrans2, IndicTransToolkit, Ollama, Qwen, Docling, Argos, LibreTranslate, NLLB, or any other unfamiliar dependency.
---

# Technical Research

**Never implement an unfamiliar API from memory.** Training-data
knowledge of a library's API can be stale, wrong, or describe a
different major version. This project explicitly forbids inventing
package names, function signatures, CLI flags, model identifiers, or
config keys — verify or say "unverified."

## Source priority (highest to lowest trust)

```text
1. Official documentation
2. Official GitHub repository (README, examples, CHANGELOG)
3. Official model card (for ML models)
4. Official issue tracker (for known limitations/bugs)
5. Peer-reviewed paper (for research models like NLLB)
6. Community discussion (Stack Overflow, forums)
7. General/secondary sources
```

Only fall back to a lower tier when a higher one is unavailable, and
say so explicitly ("official docs unreachable, using community
source X — treat as lower confidence").

## Before implementing anything unfamiliar, check

1. Does official documentation exist and is it current?
2. What is the current stable version / release?
3. What is the actual public API (function/class names, signatures)?
4. What license does it use (compatible with this project)?
5. Is it compatible with the Python version in use here?
6. What are its documented limitations (e.g. NLLB's model card
   explicitly disclaims production/document-translation use — master
   plan Section 13; don't skip disclaimers like that)?
7. Are the examples you're about to copy from actually current, or
   from an old version?
8. Record the source URL(s) and the date checked.

## Output format

For a substantial research task, write findings to `docs/research/<topic>.md`
with: what was checked, source URLs, version/release, license,
relevant API surface, limitations, and a recommendation. Add a row to
`docs/research/SOURCES.md` (Technology | Source | URL | Date checked |
Version | Relevant finding). For a quick in-conversation check (e.g.
confirming one function signature before using it), a short inline
note with the source URL is enough — don't over-produce documentation
for a one-line fact.

## Scope discipline

Research what the *current milestone* actually needs (see
`PROJECT_STATE.md`). Don't front-load research on every dependency in
the master plan before it's needed — that's wasted effort if the
architecture shifts. Exception: if the user explicitly asks for a
broad research pass across multiple technologies up front, do that
instead, but confirm the scope first since it's a large task.

## When this applies

Before writing code against any library/API/model not already used
elsewhere in this codebase, before recommending a technology choice
(e.g. "Docling vs PyMuPDF for this"), and before any claim about a
tool's capabilities, pricing, or limitations that isn't already
documented in the master plan with a source.
