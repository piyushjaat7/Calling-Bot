"""STT application service — the input-validation boundary.

The service owns everything that is *not* provider-specific: it validates
the audio upload (emptiness, size, WAV/PCM structure), extracts the PCM
payload and sample rate, and delegates the actual recognition to the
injected :class:`~backend.app.stt.ports.SttPort`. Application and REST code
depend on this class (and through it on the port abstraction) — never on a
concrete provider.
"""

from __future__ import annotations

from backend.app.config.settings import Settings, get_settings
from backend.app.stt.exceptions import (
    SttAudioTooLargeError,
    SttEmptyAudioError,
    SttUnsupportedFormatError,
)
from backend.app.stt.ports import SttPort, SttResult
from backend.app.stt.wav import parse_wav


class SttService:
    """Validates audio input and transcribes it through the STT port.

    Args:
        port: The speech-to-text port (provider abstraction).
        max_audio_bytes: Optional upload size limit; defaults to
            ``STT_MAX_AUDIO_BYTES``.
    """

    def __init__(
        self,
        port: SttPort,
        max_audio_bytes: int | None = None,
    ) -> None:
        config: Settings = get_settings()
        self._port: SttPort = port
        self._max_audio_bytes: int = (
            max_audio_bytes or config.stt_max_audio_bytes
        )

    async def transcribe(self, audio: bytes) -> SttResult:
        """Validate a WAV upload and transcribe it.

        Args:
            audio: The raw uploaded bytes (WAV container expected).

        Returns:
            The provider-independent transcription result.

        Raises:
            SttEmptyAudioError: When the payload carries no bytes.
            SttAudioTooLargeError: When the payload exceeds the limit.
            SttUnsupportedFormatError: When the payload is not a supported
                WAV/PCM file.
            SttProviderError: Propagated from the port when the provider
                fails.
            SttInvalidResponseError: Propagated from the port when the
                provider returns an unusable response.
        """
        sample_rate, pcm = self._validate_and_decode(audio)
        return await self._port.transcribe(pcm, sample_rate)

    def _validate_and_decode(self, audio: bytes) -> tuple[int, bytes]:
        """Enforce the input contract and decode the PCM payload.

        Args:
            audio: The raw uploaded bytes.

        Returns:
            A tuple of ``(sample_rate, pcm)`` for the STT port.

        Raises:
            SttEmptyAudioError / SttAudioTooLargeError /
            SttUnsupportedFormatError: On validation failure.
        """
        if not audio:
            raise SttEmptyAudioError("Audio payload is empty.")
        if len(audio) > self._max_audio_bytes:
            raise SttAudioTooLargeError(self._max_audio_bytes)
        try:
            return parse_wav(audio)
        except ValueError as exc:
            raise SttUnsupportedFormatError(
                f"Unsupported audio format: {exc}"
            ) from exc


__all__ = ["SttService"]