# Dependencies

Running log of verified dependencies for this project. Every entry
must be checked against the `dependency-verification` skill before
being added — see `.claude/skills/dependency-verification/SKILL.md`.

## streamlit
- Version: 1.63.0 (installed; `requirements.txt` pins `>=1.38`)
- Repository: https://github.com/streamlit/streamlit
- License: Apache-2.0
- Python compatibility: 3.9+
- Install: `pip install streamlit`
- Reason: Master plan Section 4.1 — fast local UI, file upload,
  selectors, previews, no separate frontend needed.
- Verified: 2026-09-08 via local `pip install` + `streamlit.__version__`.

## pymupdf
- Version: 1.28.2 (installed; `requirements.txt` pins `>=1.24`)
- Repository: https://github.com/pymupdf/PyMuPDF
- License: AGPL-3.0 (also offers a commercial license from Artifex) —
  **flag for the user**: this repo has no LICENSE file yet, and
  AGPL's copyleft terms should be reviewed before any distribution of
  this project, especially if it's ever hosted as a service.
- Python compatibility: 3.9+ (per PyPI classifiers at install time)
- Install: `pip install pymupdf` (imports as `pymupdf`; legacy `fitz`
  import alias still works but is deprecated per its own runtime
  warning — this project uses `import pymupdf as fitz`)
- Reason: Master plan Section 4.2 — span-level text/bbox/font/color
  extraction and PDF rendering, core to the whole pipeline.
- Verified: 2026-09-08 via local `pip install` + `pymupdf.VersionBind`
  + observed deprecation warning on `import fitz`.

## pydantic
- Version: 2.13.5 (installed; `requirements.txt` pins `>=2.7`)
- Repository: https://github.com/pydantic/pydantic
- License: MIT
- Python compatibility: 3.9+
- Install: `pip install pydantic`
- Reason: Master plan Section 64 — typed internal Document model
  (`core/models.py`) instead of untyped dicts.
- Verified: 2026-09-08 via local `pip install` + `pydantic.VERSION`.

## pytest (dev-only, not in requirements.txt)
- Repository: https://github.com/pytest-dev/pytest
- License: MIT
- Install: `pip install pytest` (test-time only)
- Reason: Master plan Section 54 — regression tests against fixture
  PDFs.
- Verified: 2026-09-08 via local `pip install`.
