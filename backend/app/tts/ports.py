"""Text-to-Speech external ports.

The TTS layer mirrors the STT port pattern: the application layer depends
on the abstraction (:class:`TtsPort`) and never on a concrete provider.
The contract is deliberately minimal — text in, audio out:

* :class:`TtsPort` — the synthesis contract. Implementations receive
  validated text and return provider-independent audio; every provider
  failure must be raised as one of the errors in
  :mod:`backend.app.tts.exceptions`, never a raw provider exception.
* :class:`TtsResult` — the provider-independent synthesis result. It
  carries the audio bytes plus the metadata the next telephony milestone
  needs (format, sample rate, channels, duration) without coupling the
  rest of the application to the provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class TtsPort(Protocol):
    """Provider-independent contract of a text-to-speech engine.

    Implementations return an audio result for the given text; the input
    validation (emptiness, length) lives in the
    :class:`~backend.app.tts.service.TtsService`, so every provider only
    ever sees usable input.
    """

    async def synthesize(self, text: str) -> TtsResult:
        """Synthesize speech for the given text.

        Args:
            text: The text to speak (non-empty, within the length limit).

        Returns:
            The provider-independent synthesis result.

        Raises:
            TtsProviderError: When the provider itself fails (e.g. the
                engine cannot be initialized or synthesis crashes).
            TtsInvalidOutputError: When the provider returns malformed or
                empty audio.
        """


@dataclass(frozen=True, slots=True)
class TtsResult:
    """Provider-independent result of a :class:`TtsPort` call.

    Attributes:
        audio: The generated audio bytes (WAV/PCM container).
        format: The container format of ``audio`` (default ``"wav"``).
        sample_rate: The sample rate of the audio in Hz.
        channels: The number of audio channels.
        bits_per_sample: The bits per sample of the audio.
        duration_seconds: The audio duration in seconds when the provider
            can compute it, ``None`` otherwise.
    """

    audio: bytes
    sample_rate: int
    channels: int
    bits_per_sample: int
    format: str = "wav"
    duration_seconds: float | None = None


__all__ = ["TtsPort", "TtsResult"]