# Streamlit — Research Findings

Scope: Section L. Only what's needed for the upload -> analyze ->
translate -> preview -> download workflow, verified against official
Streamlit docs (docs.streamlit.io) only.

Date checked: 2026-09-08.

---

## 1. File upload — `st.file_uploader`

Source: docs.streamlit.io/develop/api-reference/widgets/st.file_uploader
(official docs).

- **Default size limit: 200 MB per file.** Configurable two ways:
  - Global: `server.maxUploadSize` in `.streamlit/config.toml`.
  - Per-widget: `max_upload_size` parameter on the widget call itself
    (overrides the global default for that widget).
- Returns an `UploadedFile` object, which is a subclass of `BytesIO` —
  a file-like object.
  - Get raw bytes: `uploaded_file.getvalue()`.
  - Read as text: `.decode("utf-8")` on the bytes.
  - Can be passed directly anywhere a file-like object is accepted.
  - For an on-disk temp file (needed if a downstream library, e.g.
    PyMuPDF, expects a filesystem path rather than a stream), write
    `uploaded_file.getvalue()` to a `tempfile` (Python standard
    library) — this is standard Python, not a Streamlit-specific API,
    so it isn't separately verified against Streamlit docs, but is
    the documented general pattern for turning `UploadedFile` bytes
    into a path-based input.

## 2. Progress / status — `st.progress`, `st.status`

Source: docs.streamlit.io/develop/api-reference/status/st.status
(official docs).

- `st.status`: "Insert a status container to display output from
  long-running tasks." An expandable/collapsible container with a
  visual state icon (running/complete/error) and a label; can host
  arbitrary child elements (e.g. `st.write` calls) for step-by-step
  progress narration. Has three visual styles: "default," "compact,"
  "step" (the latter for timeline-style display).
- `st.progress` is the simpler numeric progress bar (0–100% or a
  float 0.0–1.0) for quantitative progress.
- Recommended combination for this project's pipeline (OCR ->
  translate -> render -> QA): `st.status` as the outer container
  narrating each pipeline stage by name, with `st.progress` nested
  inside for stages that have a meaningful sub-progress fraction
  (e.g. "translating block 12 of 40").

## 3. Preview / rendering an image — `st.image`

Not separately re-verified beyond general Streamlit API knowledge in
this pass (`st.image(data, caption=..., width=...)` displays an image
from a PIL Image, numpy array, bytes, or file path/URL) — this is a
stable, long-standing widget; the task's narrow scope note allows
skipping exhaustive re-verification here since no non-trivial or
version-sensitive API surface is being relied on (unlike
`insert_htmlbox` or `Font.text_length`, which needed source
verification). Relevant use: render `page.get_pixmap()` output (a
PyMuPDF Pixmap, convertible to PNG bytes via `pix.tobytes("png")`) via
`st.image(pix.tobytes("png"))` for page-preview panels, before/after
comparison, and diff heatmaps produced by the visual-QA layer.

## 4. Downloads — `st.download_button`

Source: docs.streamlit.io/develop/api-reference/widgets/st.download_button
(official docs).

- Parameters: `label`, `data` (string / bytes / file-like object /
  **callable**), `file_name`, `mime` (auto-detected if omitted).
- **Deferred generation via callable**: passing a callable as `data`
  defers generation until the button is actually clicked, and per the
  official docs this callable "runs on a separate thread from the
  resulting script rerun" — documented specifically to **avoid
  blocking the page script** for large files. This is directly
  relevant here: generating the final translated PDF bytes on click
  (rather than eagerly on every rerun) avoids re-running the full
  render pipeline unnecessarily.
- Default click behavior triggers a full app rerun (`on_click="rerun"`
  by default); `on_click="ignore"` avoids the rerun, and wrapping the
  button in a fragment is the documented alternative for preventing
  a full-app rerun on download.

## 5. Session state — `st.session_state`

Source: docs.streamlit.io/develop/concepts/architecture/session-state
(official docs).

- Persists variables across Streamlit's top-to-bottom script reruns
  within one user session — necessary because **every widget
  interaction re-executes the whole script from top to bottom** by
  default, so any state needed across the upload -> analyze ->
  translate -> preview -> download pipeline steps must live in
  `st.session_state`, not in plain local variables.
- API is dict-like: `st.session_state.key = value` to set,
  `st.session_state.key` or `st.session_state["key"]` to read; guard
  first-run initialization with `if 'key' not in st.session_state:`.
- Combine with widget **callbacks** (`on_click`/`on_change` functions)
  to advance a multi-step workflow's state machine without losing
  previously computed data (e.g. keep the extracted document model
  and OCR results in session state so re-running the script for a
  later step, like clicking "translate," doesn't re-run OCR).
- Caveats (per official docs): state exists only "as long as the tab
  is open and connected to the Streamlit server" — lost on server
  restart or tab close, so nothing in it should be assumed durable;
  values for `st.button`/`st.file_uploader` widgets specifically
  cannot be set programmatically via session_state (widget-owned
  state is read-only from the state dict's perspective for those
  widget types).

## 6. Long-running local computation — caching and threading guidance

Source: docs.streamlit.io/develop/concepts/architecture/caching
(official docs).

- `st.cache_data`: for functions returning **serializable** data
  (DataFrames, arrays, strings, etc.) — makes "a new copy of the data
  at each function call, making it safe against mutations and race
  conditions." Appropriate for e.g. cached OCR/translation results
  keyed by input hash.
- `st.cache_resource`: for **unserializable** shared objects — ML
  models, DB connections, file handles/threads — stored as a single
  shared instance across sessions (singleton pattern), not copied.
  Official docs explicitly frame this around model loading: "Loading
  the model takes time and slows down the app... Each session loads
  the model from scratch, which takes up a huge amount of memory" —
  i.e. this project's OCR model and translation model (e.g. an
  IndicTrans2 model, if/when adopted per CLAUDE.md) should be loaded
  via `st.cache_resource`, not reloaded per session/rerun.
- **Gap in official docs**: the caching page does **not** address
  async execution, background threading, or explicit UI-freeze
  avoidance for a single long-running inference call itself (as
  opposed to avoiding *repeated* loading via caching) — Streamlit's
  execution model is a synchronous top-to-bottom script rerun, so a
  long OCR/translation call inside the main script body **will
  block the UI thread for that session** while it runs, regardless of
  caching. Caching only avoids re-doing the same expensive work on
  every rerun; it does not make a first-time expensive call
  non-blocking.
- The one documented mechanism for non-blocking behavior found in
  this pass is specific to `st.download_button`'s callable-`data`
  path (Section 4 above), which explicitly runs on a separate thread
  — this is a narrow, button-specific case, not a general
  long-running-task solution.
- **Recommendation for this project**, flagged as reasoned
  architecture guidance rather than a directly-documented Streamlit
  pattern (since official docs don't cover it): keep the OCR/
  translation/render pipeline invocation structured so `st.status`
  (Section 2) gives the user visible progress during the blocking
  call, cache model loads via `st.cache_resource` so only the actual
  per-document inference blocks (not model startup), and cache
  per-document intermediate results via `st.cache_data` so re-runs
  triggered by unrelated widget interactions (e.g. adjusting a QA
  threshold slider) don't re-trigger OCR/translation from scratch.
  If true non-blocking background execution becomes a hard
  requirement, that would need a mechanism outside what official
  Streamlit docs document (e.g. Python's own `threading`/
  `concurrent.futures` with a manual rerun-trigger pattern) — verify
  that separately before implementing, since it is not covered by
  the sources checked in this pass.

---

## Sources

| Technology | Title | URL | Source type | Date checked | Version/release | Relevant finding |
|---|---|---|---|---|---|---|
| Streamlit | `st.file_uploader` API reference | https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader | Official docs | 2026-09-08 | current | Default 200MB limit; `server.maxUploadSize` config / `max_upload_size` param; returns `UploadedFile` (BytesIO subclass), use `.getvalue()` for bytes |
| Streamlit | `st.status` API reference | https://docs.streamlit.io/develop/api-reference/status/st.status | Official docs | 2026-09-08 | current | Expandable status container for long-running task output, distinct from the simpler `st.progress` bar |
| Streamlit | `st.download_button` API reference | https://docs.streamlit.io/develop/api-reference/widgets/st.download_button | Official docs | 2026-09-08 | current | Callable `data` param defers generation and "runs on a separate thread from the resulting script rerun" to avoid blocking |
| Streamlit | Session State concepts | https://docs.streamlit.io/develop/concepts/architecture/session-state | Official docs | 2026-09-08 | current | Dict-like persistence across reruns; scoped to the connected session/tab; button/file_uploader state can't be set via session_state |
| Streamlit | Caching concepts (`st.cache_data` vs `st.cache_resource`) | https://docs.streamlit.io/develop/concepts/architecture/caching | Official docs | 2026-09-08 | current | `cache_data` for serializable data (copied per call); `cache_resource` for shared unserializable resources like ML models (singleton); no documented async/threading guidance for blocking inference itself |
