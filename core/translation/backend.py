"""TranslationBackend — the stable interface, Milestone 5 point 3.

Any backend (mock, IndicTrans2, a future local or remote model) must
satisfy this `Protocol`. Nothing outside a concrete backend's own
module may import that backend's model-specific objects — callers only
ever see `TranslationRequest`/`TranslationResult`/`BackendInfo`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from core.translation.models import TranslationRequest, TranslationResult


class BackendInfo(BaseModel):
    name: str
    model_identifier: str
    version: str
    deterministic: bool
    device: str
    notes: str = ""


@runtime_checkable
class TranslationBackend(Protocol):
    def translate(self, request: TranslationRequest) -> TranslationResult: ...

    def translate_batch(self, requests: list[TranslationRequest]) -> list[TranslationResult]:
        """Default-implementable as a loop over `translate()`, but a
        real model backend should override this to actually batch the
        underlying inference call. Must preserve ordering: output[i]
        corresponds to requests[i] (point 10)."""
        ...

    def supported_languages(self) -> set[str]: ...

    def backend_info(self) -> BackendInfo: ...


class TranslationBackendUnavailableError(RuntimeError):
    """Raised by a backend's constructor (never at import time) when
    its runtime dependencies aren't installed/loadable — e.g.
    `IndicTrans2Backend()` on a platform where `IndicTransToolkit`
    isn't installed. Callers should catch this and fall back or skip,
    never let it propagate as an unhandled crash."""
