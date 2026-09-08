"""core/translation/registry.py — language registry tests."""

import pytest

from core.layout.models import ScriptCategory
from core.translation.registry import LANGUAGES, get_language, is_registered, model_code_for


def test_all_target_languages_registered():
    for code in ("en", "hi", "te", "ta", "kn", "ml"):
        assert code in LANGUAGES


def test_model_codes_match_verified_flores_codes():
    """Values verified against AI4Bharat's own README during the
    Milestone 1 research pass (docs/research/indictrans2.md) -- not
    re-derived from memory here."""
    assert model_code_for("en") == "eng_Latn"
    assert model_code_for("hi") == "hin_Deva"
    assert model_code_for("te") == "tel_Telu"
    assert model_code_for("ta") == "tam_Taml"
    assert model_code_for("kn") == "kan_Knda"
    assert model_code_for("ml") == "mal_Mlym"


def test_indic_languages_are_categorized_as_indic():
    for code in ("hi", "te", "ta", "kn", "ml"):
        assert LANGUAGES[code].script_category == ScriptCategory.INDIC


def test_english_is_latin():
    assert LANGUAGES["en"].script_category == ScriptCategory.LATIN


def test_unknown_code_raises_keyerror():
    with pytest.raises(KeyError):
        get_language("xx")


def test_is_registered():
    assert is_registered("hi") is True
    assert is_registered("xx") is False


def test_registry_records_font_availability_honestly():
    """Malayalam has no font downloaded yet (docs/dependencies.md) --
    the registry must not pretend otherwise."""
    assert LANGUAGES["ml"].font_file is None
    assert LANGUAGES["te"].font_file is not None
