"""core/layout/numerals.py — renderer-compatibility fallback tests.

Explicitly verifies this is a RENDERING workaround, not a translation
rule: the fallback only fires for the three affected languages, only
when native digits are actually present, and never touches anything
else in the string.
"""

from core.layout.numerals import apply_native_digit_fallback, needs_native_digit_fallback


def test_telugu_native_digits_are_substituted():
    text, changed = apply_native_digit_fallback("సంఖ్య ౧౨౩", "te")
    assert changed is True
    assert text == "సంఖ్య 123"


def test_tamil_native_digits_are_substituted():
    text, changed = apply_native_digit_fallback("எண் ௧௨௩", "ta")
    assert changed is True
    assert text == "எண் 123"


def test_kannada_native_digits_are_substituted():
    text, changed = apply_native_digit_fallback("ಸಂಖ್ಯೆ ೧೨೩", "kn")
    assert changed is True
    assert text == "ಸಂಖ್ಯೆ 123"


def test_devanagari_native_digits_are_never_touched():
    """Milestone 2 finding: Hindi's native digits render correctly --
    the fallback must not "fix" something that isn't broken."""
    original = "संख्या १२३"
    text, changed = apply_native_digit_fallback(original, "hi")
    assert changed is False
    assert text == original


def test_no_op_when_no_native_digits_present():
    text, changed = apply_native_digit_fallback("ఇది ఒక వాక్యం", "te")
    assert changed is False
    assert text == "ఇది ఒక వాక్యం"


def test_no_op_for_unrelated_language():
    text, changed = apply_native_digit_fallback("Hello 123", "en")
    assert changed is False
    assert text == "Hello 123"


def test_only_digits_are_substituted_rest_of_string_untouched():
    original = "ధర ₹500 మరియు సంఖ్య ౧౨౩ ముగింపు"
    text, changed = apply_native_digit_fallback(original, "te")
    assert changed is True
    # Everything except the native digits is byte-identical.
    assert text.replace("123", "౧౨౩") == original


def test_needs_native_digit_fallback_matches_affected_languages():
    assert needs_native_digit_fallback("te") is True
    assert needs_native_digit_fallback("ta") is True
    assert needs_native_digit_fallback("kn") is True
    assert needs_native_digit_fallback("hi") is False
    assert needs_native_digit_fallback("en") is False
    assert needs_native_digit_fallback(None) is False
