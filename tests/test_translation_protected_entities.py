"""core/translation/protected_entities.py — protected-entity tests (point 6)."""

from core.translation.protected_entities import protect, restore


def test_url_is_protected():
    text = "Visit https://example.com for details."
    protected, placeholders = protect(text)
    assert "https://example.com" not in protected
    assert any(v == "https://example.com" for v in placeholders.values())


def test_email_is_protected():
    text = "Contact support@example.com before 15 October."
    protected, placeholders = protect(text)
    assert "support@example.com" not in protected
    assert any(v == "support@example.com" for v in placeholders.values())


def test_currency_is_protected():
    text = "Total: ₹1500 due today."
    protected, placeholders = protect(text)
    assert "₹1500" not in protected


def test_date_is_protected():
    text = "Due on 15 October."
    protected, placeholders = protect(text)
    assert any("October" in v for v in placeholders.values())


def test_restore_reconstructs_original_exactly_when_untouched():
    text = "Contact support@example.com before 15 October."
    protected, placeholders = protect(text)
    restored, all_present = restore(protected, placeholders)
    assert restored == text
    assert all_present is True


def test_restore_detects_missing_placeholder():
    text = "Visit https://example.com today."
    protected, placeholders = protect(text)
    # Simulate a backend that dropped the placeholder token.
    mangled = protected.replace(next(iter(placeholders)), "")
    restored, all_present = restore(mangled, placeholders)
    assert all_present is False


def test_protect_then_restore_round_trip_with_multiple_entity_types():
    text = "Contact support@example.com or visit https://example.com. Total: ₹1500 due 15 October."
    protected, placeholders = protect(text)
    for entity in ("support@example.com", "https://example.com", "₹1500"):
        assert entity not in protected
    restored, all_present = restore(protected, placeholders)
    assert restored == text
    assert all_present is True


def test_plain_prose_is_left_untouched():
    text = "This is a simple sentence with no entities."
    protected, placeholders = protect(text)
    assert protected == text
    assert placeholders == {}
