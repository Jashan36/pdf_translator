"""LayoutRenderer — the interface the future rendering pipeline needs.

Per Milestone 2 instructions: this is ONLY the interface required by a
future renderer, not the complete translation pipeline. The actual
translation engine (Milestone 5+) stays entirely separate — this
module knows nothing about how a `TranslatedSpan.text` was produced,
only how to place it back onto a page.

Rendering path is fixed by experiment, not left open-ended: per
`docs/research/indic-rendering-proof.md` and
`docs/research/ARCHITECTURE_DECISIONS.md` Decision 7,
`page.insert_htmlbox()` is the ONLY supported text-insertion API in
this project for any Indic-script content — the classic
`insert_text`/`insert_textbox` are not shaping-capable and must not be
used for that purpose. This module only ever calls `insert_htmlbox`.
"""

from __future__ import annotations

import html as html_escape

import pymupdf
from pydantic import BaseModel, ConfigDict

from core.geometry import PdfRect
from core.models import TranslatedSpan


class RenderResult(BaseModel):
    """Outcome of one `render_translated_block` call — mirrors
    `insert_htmlbox`'s own `(spare_height, scale)` return, per the
    rendering proof's documented interpretation: `spare_height == -1`
    means the content did not fit at all."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    span_id: str
    target_rect: PdfRect
    spare_height: float
    scale: float
    clipped: bool
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.clipped


class LayoutRenderer:
    """Renders a single `TranslatedSpan` into a target rectangle on a
    live `pymupdf.Page`. Stateless except for the font `Archive` it's
    constructed with — safe to reuse across many render calls.
    """

    def __init__(self, font_archive: pymupdf.Archive | None = None):
        self.font_archive = font_archive

    def render_translated_block(
        self,
        page: pymupdf.Page,
        translated_block: TranslatedSpan,
        target_rect: pymupdf.Rect,
        css: str,
        *,
        scale_low: float = 1.0,
    ) -> RenderResult:
        """Insert `translated_block.text` into `target_rect` on `page`.

        `css` must declare the font-family used for the target
        language (see `core/pdf/redact_reinsert.py` for how the
        Milestone 2 proof builds this) — this function does not guess
        a font; that decision belongs to the caller (eventually the
        target-language font-fallback table, master plan Section 22).
        """
        text = html_escape.escape(translated_block.text)
        html = f"<p>{text}</p>"

        error: str | None = None
        try:
            spare_height, scale = page.insert_htmlbox(
                target_rect,
                html,
                css=css,
                archive=self.font_archive,
                scale_low=scale_low,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller, not swallowed
            spare_height, scale = -1.0, 0.0
            error = repr(exc)

        return RenderResult(
            span_id=translated_block.source_span_id,
            target_rect=target_rect,
            spare_height=spare_height,
            scale=scale,
            clipped=(spare_height == -1.0),
            error=error,
        )
