"""Speech-to-Text external ports.

The STT layer mirrors the Conversation Engine port pattern: the application
layer depends on the abstraction (:class:`SttPort`) and never on a concrete
provider. The contract is deliberately minimal — validated PCM audio in,
provider-independent text out:

* :class:`SttPort` — the transcription contract. Implementations receive
  the decoded PCM payload of a validated WAV upload together with its
  sample rate; the format, size and emptiness checks live in the
  :class:`~backend.app.stt.service.SttService`, so every provider only
  ever sees usable input.
* :class:`SttResult` — the provider-independent transcription result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class SttPort(Protocol):
    """Provider-independent contract of a speech-to-text engine.

    Implementations return a transcription for the given PCM audio; every
    provider failure must be raised as one of the errors in
    :mod:`backend.app.stt.exceptions` — raw provider exceptions never cross
    this boundary.
    """

    async def transcribe(self, pcm: bytes, sample_rate: int) -> SttResult:
        """Transcribe the given PCM audio.

        Args:
            pcm: The raw PCM payload (little-endian, 16-bit, mono).
            sample_rate: The sample rate of ``pcm`` in Hz.

        Returns:
            The provider-independent transcription result.

        Raises:
            SttProviderError: When the provider itself fails (e.g. the
                model cannot be loaded or recognition crashes).
            SttInvalidResponseError: When the provider returns a malformed
                or unusable response.
        """


@dataclass(frozen=True, slots=True)
class SttResult:
    """Provider-independent result of an :class:`SttPort` call.

    Attributes:
        text: The transcribed text (``""`` for silence).
    """

    text: str


__all__ = ["SttPort", "SttResult"]