"""Vosk adapter — an implementation of the :class:`~backend.app.stt.ports.SttPort`.

Talks to the local Vosk engine through its Python bindings (``vosk``
package): a fully offline, CPU-only, API-key-free recognizer that fits the
Windows development environment. The model directory comes exclusively from
:class:`~backend.app.config.settings.Settings` (``STT_VOSK_MODEL_PATH``)
unless overridden at construction time, so nothing here is hardcoded and no
model file is ever committed.

The model is loaded lazily on the first transcription (the module imports
cleanly without a model present). All failures are normalized to the clean
errors of :mod:`backend.app.stt.exceptions`; raw ``vosk`` exceptions never
escape.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from vosk import KaldiRecognizer, Model

from backend.app.config.settings import Settings, get_settings
from backend.app.core.logger import (
    LogCategory,
    LogContext,
    bind_context,
    get_category_logger,
)
from backend.app.stt.exceptions import (
    SttInvalidResponseError,
    SttProviderError,
)
from backend.app.stt.ports import SttPort, SttResult

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any

#: Caps the size of the model-load failure log.
_MAX_ERROR_DETAIL_CHARS: Final[int] = 300


class VoskAdapter(SttPort):
    """Minimal ``SttPort`` backed by a local Vosk model.

    Args:
        model_path: Directory of a Vosk model (``conf/model.conf`` +
            ``am/final.mdl``); defaults to ``STT_VOSK_MODEL_PATH``.
        model_factory: Callable building the model from ``model_path``
            (used by tests to inject a fake; defaults to ``vosk.Model``).
        recognizer_factory: Callable building a recognizer from a model and
            a sample rate (used by tests to inject a fake; defaults to
            ``vosk.KaldiRecognizer``).
    """

    def __init__(
        self,
        model_path: str | None = None,
        model_factory: Callable[[str], Any] | None = None,
        recognizer_factory: Callable[[Any, int], Any] | None = None,
    ) -> None:
        config: Settings = get_settings()
        self._model_path: str = model_path or config.stt_vosk_model_path
        self._model_factory: Callable[[str], Any] = model_factory or Model
        self._recognizer_factory: Callable[[Any, int], Any] = (
            recognizer_factory or KaldiRecognizer
        )
        self._model: Any = None
        self._log: Logger = get_category_logger(
            LogCategory.AI, module="stt.vosk"
        )

    async def transcribe(self, pcm: bytes, sample_rate: int) -> SttResult:
        """Transcribe PCM audio (see :class:`SttPort`).

        Args:
            pcm: Raw 16-bit mono PCM payload.
            sample_rate: Sample rate of ``pcm`` in Hz.

        Returns:
            The transcription result (``text == ""`` for silence).

        Raises:
            SttProviderError: When the model cannot be loaded or the
                recognizer fails.
            SttInvalidResponseError: When the recognizer returns a
                malformed or unusable response.
        """
        model: Any = self._ensure_model()
        recognizer: Any = self._recognizer_factory(model, sample_rate)
        self._log_context().debug(
            f"Transcribing {len(pcm)} PCM bytes at {sample_rate} Hz"
        )
        try:
            recognizer.AcceptWaveform(pcm)
            raw: str = recognizer.FinalResult()
        except Exception as exc:
            self._log_context().error(f"Vosk recognition failed: {exc}")
            raise SttProviderError(
                "Speech recognition failed."
            ) from exc

        text: str = self._extract_text(raw)
        self._log_context().info(
            f"Transcription completed ({len(text)} characters)"
        )
        return SttResult(text=text)

    # -- Internals -----------------------------------------------------------

    def _ensure_model(self) -> Any:
        """Load the model once and cache it.

        Returns:
            The loaded model.

        Raises:
            SttProviderError: When the model directory is missing or the
                model cannot be created.
        """
        if self._model is None:
            try:
                self._model = self._model_factory(self._model_path)
            except Exception as exc:
                detail: str = str(exc)[:_MAX_ERROR_DETAIL_CHARS]
                self._log_context().error(
                    f"Could not load Vosk model from {self._model_path}: {detail}"
                )
                raise SttProviderError(
                    f"Could not load the Vosk model from {self._model_path}."
                ) from exc
        return self._model

    @staticmethod
    def _extract_text(raw: str) -> str:
        """Return the transcription text of a recognizer response.

        Args:
            raw: The JSON string produced by the recognizer.

        Returns:
            The transcribed text (``""`` for silence).

        Raises:
            SttInvalidResponseError: When the response is not valid JSON or
                carries no usable ``text`` field.
        """
        try:
            data: Any = json.loads(raw)
        except ValueError as exc:
            raise SttInvalidResponseError(
                "STT provider returned a non-JSON response."
            ) from exc
        text: Any = data.get("text") if isinstance(data, dict) else None
        if not isinstance(text, str):
            raise SttInvalidResponseError(
                "STT provider response is missing a text field."
            )
        return text

    def _log_context(self) -> Logger:
        """Return the module logger bound with the provider context."""
        return bind_context(
            self._log, LogContext(provider="vosk")
        )


__all__ = ["VoskAdapter"]