"""core/translation/splitting.py — long-input splitting tests (point 11)."""

from core.translation.splitting import UnitSplitter


def test_short_text_not_split():
    splitter = UnitSplitter(max_chars=100)
    assert splitter.split("Short sentence.") == ["Short sentence."]


def test_long_text_splits_on_sentence_boundaries_preserving_order():
    splitter = UnitSplitter(max_chars=20)
    text = "First sentence. Second sentence. Third sentence."
    segments = splitter.split(text)
    assert segments is not None
    assert "".join(segments).replace(" ", "") == text.replace(" ", "")  # no content lost
    # Reassembling in order reproduces the sentences in the same sequence.
    assert segments[0].startswith("First")
    assert segments[-1].endswith("Third sentence.")


def test_indic_danda_punctuation_is_a_valid_boundary():
    splitter = UnitSplitter(max_chars=15)
    text = "पहला वाक्य। दूसरा वाक्य। तीसरा वाक्य।"
    segments = splitter.split(text)
    assert segments is not None
    assert len(segments) > 1


def test_unsplittable_single_sentence_returns_none_not_truncated():
    splitter = UnitSplitter(max_chars=10)
    text = "Thisisonelongwordwithnobreak"
    assert splitter.split(text) is None


def test_split_never_drops_content_for_valid_splits():
    splitter = UnitSplitter(max_chars=30)
    text = "One. Two. Three. Four. Five. Six. Seven."
    segments = splitter.split(text)
    assert segments is not None
    reconstructed = " ".join(segments)
    for word in ("One", "Two", "Three", "Four", "Five", "Six", "Seven"):
        assert word in reconstructed


def test_needs_split_boundary():
    splitter = UnitSplitter(max_chars=10)
    assert splitter.needs_split("12345") is False
    assert splitter.needs_split("12345678901") is True
