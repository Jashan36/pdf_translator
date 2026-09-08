---
name: dependency-verification
description: Verify a package/library actually exists, is current, and is license-compatible before adding it to requirements.txt or recommending "install X". Use before any pip install / requirements.txt change in this project.
---

# Dependency Verification

Never tell the user to install a package, or add one to
`requirements.txt`, without verifying it first. A plausible-sounding
package name can be wrong, abandoned, or renamed.

## Required checks before adding a dependency

1. **Package name** — confirm the exact importable/installable name
   (PyPI name can differ from the import name, e.g. `pymupdf` imports
   as `fitz` or `pymupdf`).
2. **Version** — pin or note the current stable version; don't assume
   "latest" behaves like the version you remember.
3. **Official repository** — link it.
4. **License** — confirm it's usable for this project (this repo has
   no license file yet — flag that as a gap if it becomes relevant,
   don't silently assume MIT-compatible).
5. **Python compatibility** — confirm it supports the Python version
   this project targets.
6. **Installation method** — plain `pip install`, extra system
   dependency (e.g. native libs), or something else (e.g. requires a
   separate model download)?
7. **Reason** — one sentence on why this dependency vs. an alternative
   already considered in the master plan (Section 63-64 lists the
   staged dependency plan — check whether something already covers the
   need before adding a new one).

## Record it

Append an entry to `docs/dependencies.md`:

```markdown
## <package-name>
- Version: <x.y.z>
- Repository: <url>
- License: <license>
- Python compatibility: <e.g. >=3.10>
- Install: <e.g. `pip install pymupdf`>
- Reason: <why this, vs alternatives>
- Verified: <date> via <source>
```

Create `docs/dependencies.md` if it doesn't exist yet, with a one-line
header explaining its purpose, before the first entry.

## Staged install discipline (master plan Section 63)

Don't install everything on day one. The plan's order is: `streamlit`
+ `pymupdf` first → translation provider → language detection → OCR →
Docling. Only add a dependency when the milestone that needs it is
actually being built (see `PROJECT_STATE.md` for current milestone).

## When this applies

Any `pip install`, any addition to `requirements.txt`, and any
sentence to the user of the form "you'll need to install X."
