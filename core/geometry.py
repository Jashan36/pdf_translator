"""Geometry types shared across the Document Model.

Coordinate convention (must be understood before touching any bbox in
this codebase): every `Rect`/`Quad` in this project is a
`pymupdf.Rect`/`pymupdf.Quad`, which use **PyMuPDF's** coordinate
space, not the raw PDF content-stream space:

- Origin (0, 0) is the TOP-LEFT corner of the (unrotated) page.
- x increases rightward, y increases DOWNWARD.

This differs from the raw PDF specification's own coordinate space
(origin bottom-left, y increasing upward) — PyMuPDF flips this for you
consistently across every API (`page.rect`, `get_text("dict")` boxes,
`get_images`/`get_image_rects`, `get_drawings`, `insert_htmlbox`
target rects, etc.), so as long as every geometry value in this
project comes from or is fed back into a PyMuPDF call, the convention
stays internally consistent. Do not hand-convert to "PDF space" — there
is no reason to, and doing so inconsistently is a real source of bugs
per `docs/research/pdf-internals.md`.

Per Milestone 2's instructions: geometry must remain in this
(PyMuPDF's) coordinate space, and `Rect`/`Quad` are kept as first-class
types in the in-memory model rather than flattened to arbitrary tuples
prematurely. They are still fully JSON-serializable (see the
`PdfRect`/`PdfQuad` annotated types below) so the Document Model can be
serialized without ever touching a raw PyMuPDF object directly (see
`core/serialization.py`).
"""

from __future__ import annotations

from typing import Annotated, Any

import pymupdf
from pydantic import PlainSerializer, PlainValidator


def _validate_rect(value: Any) -> pymupdf.Rect:
    if isinstance(value, pymupdf.Rect):
        return value
    if isinstance(value, dict):
        return pymupdf.Rect(value["x0"], value["y0"], value["x1"], value["y1"])
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return pymupdf.Rect(*value)
    raise TypeError(f"Cannot construct pymupdf.Rect from {value!r}")


def _serialize_rect(value: pymupdf.Rect) -> dict:
    return {"x0": value.x0, "y0": value.y0, "x1": value.x1, "y1": value.y1}


def _validate_quad(value: Any) -> pymupdf.Quad:
    if isinstance(value, pymupdf.Quad):
        return value
    if isinstance(value, dict):
        return pymupdf.Quad(
            tuple(value["ul"]), tuple(value["ur"]), tuple(value["ll"]), tuple(value["lr"])
        )
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return pymupdf.Quad(*value)
    raise TypeError(f"Cannot construct pymupdf.Quad from {value!r}")


def _serialize_quad(value: pymupdf.Quad) -> dict:
    return {
        "ul": tuple(value.ul),
        "ur": tuple(value.ur),
        "ll": tuple(value.ll),
        "lr": tuple(value.lr),
    }


# Use these as field types anywhere a bbox/quad is stored on a model.
# The value held in memory is a real pymupdf.Rect/Quad (with all its
# methods: .width, .height, .intersects(), .contains(), ...); pydantic
# validates dict/list input into one and serializes it back out to a
# plain JSON-compatible dict — no raw PyMuPDF object ever hits JSON.
PdfRect = Annotated[
    pymupdf.Rect,
    PlainValidator(_validate_rect),
    PlainSerializer(_serialize_rect, return_type=dict),
]
PdfQuad = Annotated[
    pymupdf.Quad,
    PlainValidator(_validate_quad),
    PlainSerializer(_serialize_quad, return_type=dict),
]
