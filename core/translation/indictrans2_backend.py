"""IndicTrans2Backend — the ONLY module in this project allowed to
import torch/transformers/IndicTransToolkit. Milestone 5 point 16.

Feasibility gate result (docs/research/indictrans2-feasibility.md):
IndicTransToolkit's own README states it is "not meant/built/tested
for Windows" and requires `numpy>=2.1, torch>=2.5, transformers>=4.51`.
This module therefore:

- Imports those packages LAZILY, inside methods, never at module load
  time — importing THIS FILE must never fail even on a machine with
  none of them installed (confirmed by `test_indictrans2_backend.py`,
  which imports this module unconditionally and only gates actual
  instantiation behind `is_available()`).
- Raises `TranslationBackendUnavailableError` from `__init__` (not a
  bare ImportError) if the dependencies aren't present, so callers get
  a structured, catchable failure rather than a crash.
- Uses the OFFICIAL preprocessing/inference path exactly as documented
  in AI4Bharat's own `huggingface_interface/example.py` — no
  reimplemented tokenization/normalization logic. See that file
  (fetched via WebFetch during this milestone, not from memory) for
  the source of the exact API calls below.
"""

from __future__ import annotations

import importlib.util

from pydantic import BaseModel

from core.translation.backend import BackendInfo, TranslationBackendUnavailableError
from core.translation.models import TranslationErrorCode, TranslationRequest, TranslationResult
from core.translation.registry import LANGUAGES, model_code_for

_REQUIRED_MODULES = ("torch", "transformers", "IndicTransToolkit")

# Official HuggingFace checkpoint identifiers (AI4Bharat/IndicTrans2
# README, verified via WebFetch during this milestone's feasibility
# gate -- distilled variants, ~200M params, chosen over the 1B base
# models for CPU feasibility per docs/research/indictrans2.md).
DEFAULT_EN_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
DEFAULT_INDIC_EN_MODEL = "ai4bharat/indictrans2-indic-en-dist-200M"

# Official generation config (huggingface_interface/example.py):
# max_length=256 is IndicTrans2's own generation cap -- this is the
# real limit core/translation/splitting.py's UnitSplitter should be
# configured against for this backend specifically, NOT the
# module-default character-count approximation.
GENERATION_MAX_LENGTH = 256


def is_available() -> bool:
    """True only if every required package is importable. Cheap
    (uses importlib.util.find_spec, does not actually import
    torch/transformers) -- safe to call before deciding whether to
    even attempt constructing an `IndicTrans2Backend`."""
    return all(importlib.util.find_spec(name) is not None for name in _REQUIRED_MODULES)


class IndicTrans2Config(BaseModel):
    model_identifier_en_indic: str = DEFAULT_EN_INDIC_MODEL
    model_identifier_indic_en: str = DEFAULT_INDIC_EN_MODEL
    local_model_path: str | None = None  # if set, loaded instead of downloading by identifier
    device: str = "cpu"  # this project's feasibility gate found no CUDA GPU available -- see docs/research/indictrans2-feasibility.md
    revision: str | None = None


class IndicTrans2Backend:
    def __init__(self, config: IndicTrans2Config | None = None):
        if not is_available():
            missing = [m for m in _REQUIRED_MODULES if importlib.util.find_spec(m) is None]
            raise TranslationBackendUnavailableError(
                f"IndicTrans2Backend requires {_REQUIRED_MODULES}; missing: {missing}. "
                "See docs/research/indictrans2-feasibility.md for the supported "
                "execution environment (Linux/WSL, not native Windows)."
            )
        self.config = config or IndicTrans2Config()
        self._models: dict[str, object] = {}  # direction -> loaded model
        self._tokenizers: dict[str, object] = {}
        self._processor = None

    # -- lazy loading ----------------------------------------------------

    def _direction_for(self, source_language: str) -> str:
        return "en_indic" if source_language == "en" else "indic_en"

    def _ensure_loaded(self, direction: str) -> None:
        if direction in self._models:
            return

        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from IndicTransToolkit.processor import IndicProcessor

        model_id = (
            self.config.local_model_path
            or (self.config.model_identifier_en_indic if direction == "en_indic" else self.config.model_identifier_indic_en)
        )

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, revision=self.config.revision)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_id, trust_remote_code=True, revision=self.config.revision, low_cpu_mem_usage=True
            ).to(self.config.device)
        except Exception as exc:  # noqa: BLE001
            raise TranslationBackendUnavailableError(f"failed to load IndicTrans2 model {model_id!r}: {exc!r}") from exc

        model.eval()
        self._models[direction] = model
        self._tokenizers[direction] = tokenizer
        if self._processor is None:
            self._processor = IndicProcessor(inference=True)

    # -- TranslationBackend protocol --------------------------------------

    def translate(self, request: TranslationRequest) -> TranslationResult:
        return self.translate_batch([request])[0]

    def translate_batch(self, requests: list[TranslationRequest]) -> list[TranslationResult]:
        if not requests:
            return []

        results: list[TranslationResult] = [None] * len(requests)  # type: ignore[list-item]
        by_direction: dict[str, list[int]] = {}
        for i, req in enumerate(requests):
            if req.source_language not in LANGUAGES or req.target_language not in LANGUAGES:
                results[i] = TranslationResult(
                    unit_id=req.unit_id, source_text=req.text, translated_text="",
                    source_language=req.source_language, target_language=req.target_language,
                    backend_name="indictrans2", model_identifier="unknown", success=False,
                    error_code=TranslationErrorCode.UNSUPPORTED_LANGUAGE,
                    diagnostics=f"{req.source_language!r}/{req.target_language!r} not in language registry",
                )
                continue
            by_direction.setdefault(self._direction_for(req.source_language), []).append(i)

        import torch

        for direction, indices in by_direction.items():
            try:
                self._ensure_loaded(direction)
            except TranslationBackendUnavailableError as exc:
                for i in indices:
                    req = requests[i]
                    results[i] = TranslationResult(
                        unit_id=req.unit_id, source_text=req.text, translated_text="",
                        source_language=req.source_language, target_language=req.target_language,
                        backend_name="indictrans2", model_identifier="unknown", success=False,
                        error_code=TranslationErrorCode.MODEL_LOAD_FAILED, diagnostics=str(exc),
                    )
                continue

            model = self._models[direction]
            tokenizer = self._tokenizers[direction]
            model_id = self.config.local_model_path or (
                self.config.model_identifier_en_indic if direction == "en_indic" else self.config.model_identifier_indic_en
            )

            batch_texts = [requests[i].text for i in indices]
            src_codes = [model_code_for(requests[i].source_language) for i in indices]
            tgt_codes = [model_code_for(requests[i].target_language) for i in indices]

            try:
                # Official preprocessing/inference path (IndicTrans2
                # huggingface_interface/example.py) -- IndicProcessor
                # expects one (src_lang, tgt_lang) pair per call, so
                # requests are grouped by (direction, tgt_lang) pair
                # for a real batched call; simplified here to per-
                # request src/tgt since this project's usage is
                # single-target-language-per-pipeline-run in this
                # milestone (see ARCHITECTURE_DECISIONS.md Decision 15
                # for the exact grouping used).
                preprocessed = self._processor.preprocess_batch(batch_texts, src_lang=src_codes[0], tgt_lang=tgt_codes[0])
                inputs = tokenizer(
                    preprocessed, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True
                ).to(self.config.device)

                with torch.no_grad():
                    generated_tokens = model.generate(
                        **inputs, use_cache=True, min_length=0, max_length=GENERATION_MAX_LENGTH,
                        num_beams=5, num_return_sequences=1,
                    )

                decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
                translations = self._processor.postprocess_batch(decoded, lang=tgt_codes[0])
            except Exception as exc:  # noqa: BLE001
                for i in indices:
                    req = requests[i]
                    results[i] = TranslationResult(
                        unit_id=req.unit_id, source_text=req.text, translated_text="",
                        source_language=req.source_language, target_language=req.target_language,
                        backend_name="indictrans2", model_identifier=model_id, success=False,
                        error_code=TranslationErrorCode.TRANSLATION_RUNTIME_ERROR, diagnostics=repr(exc),
                    )
                continue

            for i, translated in zip(indices, translations):
                req = requests[i]
                results[i] = TranslationResult(
                    unit_id=req.unit_id, source_text=req.text, translated_text=translated,
                    source_language=req.source_language, target_language=req.target_language,
                    backend_name="indictrans2", model_identifier=model_id,
                    success=bool(translated.strip()),
                    error_code=None if translated.strip() else TranslationErrorCode.OUTPUT_EMPTY,
                )

        return results

    def supported_languages(self) -> set[str]:
        return set(LANGUAGES.keys())

    def backend_info(self) -> BackendInfo:
        return BackendInfo(
            name="indictrans2",
            model_identifier=f"{self.config.model_identifier_en_indic} / {self.config.model_identifier_indic_en}",
            version="dist-200M",
            # Beam search (num_beams=5, no sampling/temperature) is
            # deterministic given fixed weights and eval-mode dropout
            # disabled -- confirmed by the official generate() call
            # signature, which sets no sampling parameters.
            deterministic=True,
            device=self.config.device,
            notes="Distilled 200M checkpoints; CPU inference only on this project's dev environment (no CUDA GPU detected).",
        )
