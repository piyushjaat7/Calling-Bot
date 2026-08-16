"""Pyttsx3 adapter — an implementation of the :class:`~backend.app.tts.ports.TtsPort`.

Talks to the local Windows SAPI5 engine through the ``pyttsx3`` package: a
fully offline, API-key-free synthesizer that uses the voices already
installed with Windows (no model downloads, no internet, no GPU). The voice
selection comes exclusively from
:class:`~backend.app.config.settings.Settings` (``TTS_PYTTSX3_VOICE``,
empty = system default) unless overridden at construction time, so nothing
here is hardcoded.

The engine is initialized lazily on the first synthesis (the module imports
cleanly without a working SAPI5 setup). Synthesis writes a temporary WAV
file that is read back and removed immediately; the output is validated and
normalized to a provider-independent
:class:`~backend.app.tts.ports.TtsResult`. All failures are normalized to
the clean errors of :mod:`backend.app.tts.exceptions`; raw ``pyttsx3``
exceptions never escape.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pyttsx3

from backend.app.config.settings import Settings, get_settings
from backend.app.core.logger import (
    LogCategory,
    LogContext,
    bind_context,
    get_category_logger,
)
from backend.app.tts.exceptions import (
    TtsInvalidOutputError,
    TtsProviderError,
)
from backend.app.tts.ports import TtsPort, TtsResult
from backend.app.tts.wav import inspect_wav

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any


class Pyttsx3Adapter(TtsPort):
    """Minimal ``TtsPort`` backed by the local SAPI5 engine.

    Args:
        engine_factory: Callable building a fresh ``pyttsx3`` engine (used
            by tests to inject a fake; defaults to ``pyttsx3.init``).
        voice: SAPI5 voice identifier; defaults to ``TTS_PYTTSX3_VOICE``
            (empty = system default voice).
    """

    def __init__(
        self,
        engine_factory: Callable[[], Any] | None = None,
        voice: str | None = None,
    ) -> None:
        config: Settings = get_settings()
        self._engine_factory: Callable[[], Any] = engine_factory or pyttsx3.init
        self._voice: str = voice if voice is not None else config.tts_pyttsx3_voice
        self._engine: Any = None
        self._log: Logger = get_category_logger(
            LogCategory.AI, module="tts.pyttsx3"
        )

    async def synthesize(self, text: str) -> TtsResult:
        """Synthesize speech for the given text (see :class:`TtsPort`).

        Args:
            text: The text to speak.

        Returns:
            The synthesis result carrying the WAV bytes and metadata.

        Raises:
            TtsProviderError: When the engine cannot be initialized or
                synthesis fails / produces no audio file.
            TtsInvalidOutputError: When the engine writes malformed or
                empty audio.
        """
        engine: Any = self._ensure_engine()
        fd: int
        path: str
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="tts_")
        os.close(fd)
        try:
            try:
                engine.save_to_file(text, path)
                engine.runAndWait()
            except Exception as exc:
                self._log_context().error(f"Pyttsx3 synthesis failed: {exc}")
                raise TtsProviderError(
                    "Speech synthesis failed."
                ) from exc
            try:
                audio: bytes = await asyncio.to_thread(self._read_audio_file, path)
            except OSError as exc:
                self._log_context().error(
                    f"Pyttsx3 produced no audio file at {path}"
                )
                raise TtsProviderError(
                    "Speech synthesis produced no audio file."
                ) from exc
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        result: TtsResult = self._build_result(audio)
        self._log_context().info(
            f"Synthesis completed ({len(audio)} audio bytes, "
            f"{result.duration_seconds:.3f} s)"
        )
        return result

    # -- Internals -----------------------------------------------------------

    @staticmethod
    def _read_audio_file(path: str) -> bytes:
        """Read the synthesized audio bytes back from disk.

        Args:
            path: The path the engine wrote to.

        Returns:
            The raw audio bytes.

        Raises:
            OSError: When the file does not exist or cannot be read.
        """
        with open(path, "rb") as audio_file:
            return audio_file.read()

    def _ensure_engine(self) -> Any:
        """Initialize the engine once and cache it.

        Returns:
            The initialized engine.

        Raises:
            TtsProviderError: When the engine cannot be created or the
                configured voice cannot be applied.
        """
        if self._engine is None:
            try:
                engine: Any = self._engine_factory()
                if self._voice:
                    engine.setProperty("voice", self._voice)
                self._engine = engine
            except Exception as exc:
                self._log_context().error(
                    f"Could not initialize the Pyttsx3 engine: {exc}"
                )
                raise TtsProviderError(
                    "Could not initialize the text-to-speech engine."
                ) from exc
        return self._engine

    def _build_result(self, audio: bytes) -> TtsResult:
        """Validate the engine output and build the port result.

        Args:
            audio: The bytes written by the engine.

        Returns:
            The provider-independent synthesis result.

        Raises:
            TtsInvalidOutputError: When the audio is malformed, empty or
                not a PCM WAV payload.
        """
        try:
            info = inspect_wav(audio)
        except ValueError as exc:
            self._log_context().error(f"Synthesized audio is invalid: {exc}")
            raise TtsInvalidOutputError(
                f"Synthesized audio is invalid: {exc}"
            ) from exc
        if info.pcm_bytes == 0:
            self._log_context().error("Synthesized audio carries no samples")
            raise TtsInvalidOutputError(
                "Synthesized audio carries no samples."
            )
        duration: float = (
            info.pcm_bytes
            * 8
            / (info.sample_rate * info.channels * info.bits_per_sample)
        )
        return TtsResult(
            audio=audio,
            sample_rate=info.sample_rate,
            channels=info.channels,
            bits_per_sample=info.bits_per_sample,
            duration_seconds=duration,
        )

    def _log_context(self) -> Logger:
        """Return the module logger bound with the provider context."""
        return bind_context(self._log, LogContext(provider="pyttsx3"))


__all__ = ["Pyttsx3Adapter"]