"""TextMeasurer — isolated render-to-scratch-page measurement.

Per Milestone 2's finding, `Font.text_length()` (naive glyph-advance
width) does not reliably predict `insert_htmlbox`'s actual
HarfBuzz-shaped layout for Indic text, and `insert_htmlbox`'s own
line-box model differs from PyMuPDF's extracted-bbox tightness. There
is therefore no trustworthy analytical formula to build the fit engine
on — per this milestone's explicit instruction (point E), measurement
is done by actually calling `insert_htmlbox` on a throwaway page that
is never saved, shown, or associated with the real document.

This keeps the fit engine's decisions grounded in the exact rendering
path (`insert_htmlbox`) that will later be used for real, rather than
an approximation that could diverge from it.
"""

from __future__ import annotations

import html as html_escape

import pymupdf
from pydantic import BaseModel, ConfigDict

from core.geometry import PdfRect


class MeasurementResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fits: bool
    spare_height: float
    scale: float
    error: str | None = None


class TextMeasurer:
    """Stateless except for the font `Archive` it wraps -- safe to
    reuse across many `measure()` calls. Each call opens and discards
    its own scratch `pymupdf.Document`; nothing persists between calls
    and nothing here ever touches a real source PDF."""

    def __init__(self, font_dir: str):
        self.font_dir = font_dir
        self.archive = pymupdf.Archive(font_dir)

    def measure(
        self,
        text: str,
        rect: pymupdf.Rect,
        *,
        font_family: str,
        font_filename: str,
        font_size: float,
        line_height: float = 1.15,
        alignment: str = "left",
        scale_low: float = 1.0,
    ) -> MeasurementResult:
        """Renders `text` into `rect` on a throwaway page and reports
        whether it fit at exactly `font_size` (when `scale_low=1.0`,
        the default -- any required shrink below that is a failure,
        which is what lets the fit engine control font size itself
        rather than delegating to `insert_htmlbox`'s own auto-shrink).
        """
        # The scratch page must be large enough to contain `rect` at
        # its own (possibly large) page coordinates -- this is a
        # measurement-only page size, unrelated to any real page.
        page_width = max(200.0, rect.x1 + 50.0)
        page_height = max(200.0, rect.y1 + 50.0)

        doc = pymupdf.open()
        try:
            page = doc.new_page(width=page_width, height=page_height)
            css = (
                f"@font-face {{font-family: {font_family}; src: url({font_filename});}}\n"
                f"* {{font-family: {font_family}; font-size: {font_size}px; "
                f"line-height: {line_height}; text-align: {alignment};}}"
            )
            html = f"<p>{html_escape.escape(text)}</p>"
            try:
                spare_height, scale = page.insert_htmlbox(
                    rect, html, css=css, archive=self.archive, scale_low=scale_low
                )
            except Exception as exc:  # noqa: BLE001 - surfaced to the caller, not swallowed
                return MeasurementResult(fits=False, spare_height=-1.0, scale=0.0, error=repr(exc))

            return MeasurementResult(fits=(spare_height != -1.0), spare_height=spare_height, scale=scale)
        finally:
            doc.close()

    def measure_required_height(
        self,
        text: str,
        width: float,
        *,
        font_family: str,
        font_filename: str,
        font_size: float,
        line_height: float = 1.15,
        alignment: str = "left",
        generous_height: float = 3000.0,
    ) -> float:
        """Diagnostic helper: how tall a box of the given `width` would
        actually need to be to fit `text` at `font_size` without
        clipping. Used only for `TextFitResult` diagnostics (overflow
        amount, line-count estimate) -- never part of the pass/fail
        decision path itself, which always uses `measure()` against
        the real candidate rect."""
        probe_rect = pymupdf.Rect(0, 0, width, generous_height)
        result = self.measure(
            text,
            probe_rect,
            font_family=font_family,
            font_filename=font_filename,
            font_size=font_size,
            line_height=line_height,
            alignment=alignment,
            scale_low=1.0,
        )
        if result.error is not None or result.spare_height < 0:
            # Even the generous probe wasn't tall enough -- return the
            # probe height itself as a lower-bound signal rather than
            # a misleading negative number.
            return generous_height
        return generous_height - result.spare_height
