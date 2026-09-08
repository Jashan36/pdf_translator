"""Protected-entity placeholder policy — Milestone 5 point 6.

Deliberately simple and deterministic per this milestone's explicit
instruction ("Do NOT build sophisticated semantic grouping yet. Build
a deterministic, testable initial policy."). Regex-based detection of
URLs, emails, currency amounts, and numeric values (which subsumes
simple dates/phone-number-shaped digit sequences at this policy's
level of sophistication) — NOT a full NER/localization system. Known
limitation, not hidden: this will not catch every real-world date
format or brand name; `docs/dependencies.md`/`ARCHITECTURE_DECISIONS.md`
records this as a deliberate v1 scope boundary.

Protect BEFORE sending text to a translation backend; restore AFTER.
The translated output must restore protected entities EXACTLY — no
"deliberate localization rule" (e.g. date reformatting) exists yet.
"""

from __future__ import annotations

import re

# Order matters: URL before EMAIL (an email inside a mailto: URL should
# not be double-matched), CURRENCY before NUMBER (a currency amount
# should not also match the bare-number pattern).
_URL = re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CURRENCY = re.compile(r"[₹$€£]\s?\d[\d,]*\.?\d*")
_DATE = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"  # 15/10/2024, 10-15-2024
    r"|\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)(\s+\d{2,4})?\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"\b\d[\d,]*\.?\d*%?\b")

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("URL", _URL),
    ("EMAIL", _EMAIL),
    ("CURRENCY", _CURRENCY),
    ("DATE", _DATE),
    ("NUMBER", _NUMBER),
]


def protect(text: str) -> tuple[str, dict[str, str]]:
    """Returns (text_with_placeholders, {placeholder_token: original_value})."""
    placeholders: dict[str, str] = {}
    counter = 0
    protected_text = text

    for kind, pattern in _PATTERNS:

        def _replace(match: re.Match, kind: str = kind) -> str:
            nonlocal counter
            token = f"__PROT_{kind}_{counter}__"
            placeholders[token] = match.group(0)
            counter += 1
            return token

        protected_text = pattern.sub(_replace, protected_text)

    return protected_text, placeholders


def restore(text: str, placeholders: dict[str, str]) -> tuple[str, bool]:
    """Returns (restored_text, all_placeholders_present). If a
    translation backend dropped or mangled a placeholder token,
    `all_placeholders_present` is False -- callers (the translation
    pipeline) should treat that as a PLACEHOLDER_MISMATCH error, not
    silently ship partially-restored text."""
    restored = text
    all_present = True
    for token, original in placeholders.items():
        if token in restored:
            restored = restored.replace(token, original)
        else:
            all_present = False
    return restored, all_present
