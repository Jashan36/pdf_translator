"""Long-input splitting policy — Milestone 5 point 11.

IndicTrans2's own inference code (confirmed via the official
`huggingface_interface/example.py`) calls `model.generate(..., max_length=256)`
— generation is capped at 256 tokens. Silent truncation loses source
content, which this project's rules forbid. This module NEVER
truncates; it either produces an ordered list of segments that
together cover the whole input, or returns `None` to signal a
structured `UNIT_SPLIT_FAILED` (point 12) that the caller must not
swallow.

The split boundary is a deterministic sentence-boundary regex (Latin
`. ! ?` and Devanagari/Indic `।`), not a real NLP sentence segmenter —
matches this milestone's "deterministic, testable initial policy"
instruction (point 5). The length threshold is a CHARACTER count, not
an actual token count: character-to-subword-token ratio varies by
script and tokenizer, so this is a conservative approximation,
documented as such, not an exact token-accurate limit. A backend that
knows its own tokenizer's real limit can pass a smaller/larger
`max_chars` to `UnitSplitter` accordingly.
"""

from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।])\s+")


class UnitSplitter:
    def __init__(self, max_chars: int = 800):
        self.max_chars = max_chars

    def needs_split(self, text: str) -> bool:
        return len(text) > self.max_chars

    def split(self, text: str) -> list[str] | None:
        """Ordered segments covering the whole input, or `None` if a
        single sentence alone still exceeds `max_chars` (no safe split
        point exists) — the caller must treat `None` as
        `UNIT_SPLIT_FAILED`, never silently truncate to fit."""
        if not self.needs_split(text):
            return [text]

        sentences = [s for s in _SENTENCE_BOUNDARY.split(text) if s]
        segments: list[str] = []
        current = ""

        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= self.max_chars:
                current = candidate
                continue

            if current:
                segments.append(current)
            if len(sentence) > self.max_chars:
                return None  # a single sentence alone is too long -- cannot safely split further
            current = sentence

        if current:
            segments.append(current)

        return segments if segments else None
