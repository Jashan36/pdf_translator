"""core/translation/indictrans2_backend.py — interface tests.

Point 20: "If IndicTrans2 is unavailable on Windows, that MUST NOT
make the entire test suite fail." Every test here either checks
behavior that doesn't require the real dependencies, or is gated
behind `is_available()` with `pytest.mark.skipif` so it simply skips
(not fails, not errors) when torch/transformers/IndicTransToolkit
aren't installed -- which is the actual state of this project's
Windows dev environment per the Milestone 5 feasibility gate
(`docs/research/indictrans2-feasibility.md`).
"""

import pytest

from core.translation.backend import TranslationBackendUnavailableError
from core.translation.indictrans2_backend import (
    GENERATION_MAX_LENGTH,
    IndicTrans2Backend,
    IndicTrans2Config,
    is_available,
)


def test_module_imports_unconditionally():
    """The mere act of importing this module must never fail, even
    with zero of its runtime dependencies installed -- confirmed by
    this test file's own successful collection."""
    import core.translation.indictrans2_backend  # noqa: F401


def test_is_available_returns_a_bool_without_raising():
    assert isinstance(is_available(), bool)


def test_official_generation_config_matches_upstream():
    """Verified via WebFetch against AI4Bharat's own
    huggingface_interface/example.py during this milestone -- not
    from memory."""
    assert GENERATION_MAX_LENGTH == 256


def test_default_model_identifiers_are_the_distilled_checkpoints():
    config = IndicTrans2Config()
    assert "dist-200M" in config.model_identifier_en_indic
    assert "dist-200M" in config.model_identifier_indic_en
    assert config.device == "cpu"


@pytest.mark.skipif(is_available(), reason="dependencies ARE installed -- this tests the unavailable path specifically")
def test_constructing_backend_raises_structured_error_when_unavailable():
    with pytest.raises(TranslationBackendUnavailableError):
        IndicTrans2Backend()


@pytest.mark.skipif(not is_available(), reason="torch/transformers/IndicTransToolkit not installed on this environment")
def test_live_backend_translates_a_known_sentence():
    """Only runs when the real dependencies are actually present --
    see docs/research/indictrans2-feasibility.md for whether that's
    true on this project's Windows dev machine (it is not, as of this
    milestone) versus a supported Linux/WSL environment."""
    from core.translation.models import TranslationRequest

    backend = IndicTrans2Backend()
    result = backend.translate(
        TranslationRequest(unit_id="1", text="Hello, how are you?", source_language="en", target_language="hi")
    )
    assert result.success
    assert result.translated_text.strip()
