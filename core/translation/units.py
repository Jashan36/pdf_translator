"""TranslationUnit — Milestone 5 point 5.

Deliberately simple grouping policy (explicitly instructed: "Do NOT
build sophisticated semantic grouping yet"): one translation unit per
TEXT block, carrying ALL of that block's span_ids so multi-span lines
(e.g. "Total" + "₹" + "1500" as three separately-styled PDF spans)
become ONE translation request, not three independent ones.

Known limitation, stated plainly: Milestone 4's pipeline
(`core/pipeline/`) still plans one redaction/reinsertion region per
individual `SourceSpan.span_id`. For a unit spanning multiple spans,
`core/translation/pipeline_bridge.py` maps the unit's translated text
back onto only the FIRST member span's bbox for actual PDF mutation —
correct grouping/translation happens here, but multi-span PDF
rendering as one combined region is not yet built (that would extend
Milestone 4's architecture, which this milestone is explicitly told
not to redesign). Every project fixture so far has one span per
translatable line, so this limitation doesn't affect any current
end-to-end test, but it is a real, documented gap for future
multi-span content.
"""

from __future__ import annotations

import pymupdf
from pydantic import BaseModel, ConfigDict

from core.geometry import PdfRect
from core.models import BlockType, Document


class TranslationUnit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    unit_id: str  # = first member span's span_id, for Milestone 4 pipeline-bridge compatibility
    text: str
    source_language: str
    span_ids: list[str]
    page_index: int
    bbox: PdfRect  # union of every member span's bbox


def build_units_from_document(document: Document, source_language: str) -> list[TranslationUnit]:
    units: list[TranslationUnit] = []
    for page_index, page in enumerate(document.pages):
        for block in page.blocks:
            if block.block_type != BlockType.TEXT or not block.raw_text.strip():
                continue
            span_ids = [span.span_id for line in block.lines for span in line.spans]
            if not span_ids:
                continue

            bbox = pymupdf.Rect(block.bbox)
            for line in block.lines:
                for span in line.spans:
                    bbox |= span.bbox

            units.append(
                TranslationUnit(
                    unit_id=span_ids[0],
                    text=block.raw_text,
                    source_language=source_language,
                    span_ids=span_ids,
                    page_index=page_index,
                    bbox=bbox,
                )
            )
    return units
