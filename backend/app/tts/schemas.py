"""TTS request/response schemas.

Strict, validated Pydantic models exposing the TTS result to the HTTP
layer. Responses serialize only the documented envelope and never leak
provider internals. The generated audio is returned base64-encoded inside
the JSON envelope (with its metadata), so the API stays provider-neutral
and clients can verify or replay the audio without extra round-trips.
"""

from __future__ import annotations

import base64

from pydantic import BaseModel, ConfigDict

from backend.app.tts.ports import TtsResult


class SynthesizeRequest(BaseModel):
    """Request body of ``POST /tts/synthesize``.

    Attributes:
        text: The text to speak (validated by the TTS service).
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    text: str


class SynthesisData(BaseModel):
    """Serialized view of a synthesis result.

    Attributes:
        format: The audio container format (``"wav"``).
        sample_rate: The sample rate of the audio in Hz.
        channels: The number of audio channels.
        bits_per_sample: The bits per sample of the audio.
        duration_seconds: The audio duration in seconds when available.
        size_bytes: The size of the audio payload in bytes.
        audio_base64: The audio bytes base64-encoded.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    format: str
    sample_rate: int
    channels: int
    bits_per_sample: int
    duration_seconds: float | None
    size_bytes: int
    audio_base64: str

    @classmethod
    def from_result(cls, result: TtsResult) -> SynthesisData:
        """Build the serialized view from a domain result.

        Args:
            result: The domain synthesis result to serialize.

        Returns:
            The validated data view of the result.
        """
        return cls(
            format=result.format,
            sample_rate=result.sample_rate,
            channels=result.channels,
            bits_per_sample=result.bits_per_sample,
            duration_seconds=result.duration_seconds,
            size_bytes=len(result.audio),
            audio_base64=base64.b64encode(result.audio).decode("ascii"),
        )


class TtsResponse(BaseModel):
    """Success envelope returned by every TTS endpoint."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    message: str
    data: SynthesisData


__all__ = ["SynthesisData", "SynthesizeRequest", "TtsResponse"]