"""WAV header inspection for TTS output validation.

Reads the RIFF/WAVE container of a synthesized audio payload and reports
its PCM layout (sample rate, channels, bits per sample, payload size).
Unlike the STT parser (:mod:`backend.app.stt.wav`), this reader is generic:
it accepts any PCM layout (mono or stereo, 8- or 16-bit, any rate) because
providers may legitimately emit different configurations — the metadata is
surfaced to the caller instead of being rejected. Only structural
requirements are enforced (RIFF/WAVE container, PCM codec, non-empty
``data`` chunk).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

#: RIFF/WAVE file header size (``RIFF`` + size + ``WAVE``).
_RIFF_HEADER_SIZE: int = 12

#: Minimum size of a ``fmt `` chunk payload (always 16 for PCM).
_FMT_CHUNK_SIZE: int = 16


@dataclass(frozen=True, slots=True)
class WavInfo:
    """Parsed layout of a WAV payload.

    Attributes:
        codec: The ``fmt `` audio format code (1 = PCM).
        channels: The number of audio channels.
        sample_rate: The sample rate in Hz.
        bits_per_sample: The bits per sample.
        pcm_bytes: The size of the ``data`` chunk payload in bytes.
    """

    codec: int
    channels: int
    sample_rate: int
    bits_per_sample: int
    pcm_bytes: int


def inspect_wav(audio: bytes) -> WavInfo:
    """Validate a WAV payload and extract its PCM layout.

    Args:
        audio: The raw audio bytes to inspect.

    Returns:
        The parsed layout of the payload.

    Raises:
        ValueError: When the payload is not a well-formed PCM WAV file
            with a non-empty ``data`` chunk.
    """
    if len(audio) < _RIFF_HEADER_SIZE:
        raise ValueError("payload is too short to be a WAV file")
    if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise ValueError("payload is missing the RIFF/WAVE container")

    fmt: WavInfo | None = None
    offset: int = _RIFF_HEADER_SIZE
    while offset + 8 <= len(audio):
        chunk_id: bytes = audio[offset : offset + 4]
        (chunk_size,) = struct.unpack_from("<I", audio, offset + 4)
        offset += 8
        payload: bytes = audio[offset : offset + chunk_size]
        if len(payload) < chunk_size:
            raise ValueError("WAV chunk extends beyond the end of the payload")
        if chunk_id == b"fmt ":
            fmt = _parse_fmt(payload)
        elif chunk_id == b"data":
            if fmt is None:
                raise ValueError("data chunk appears before the fmt chunk")
            return WavInfo(
                codec=fmt.codec,
                channels=fmt.channels,
                sample_rate=fmt.sample_rate,
                bits_per_sample=fmt.bits_per_sample,
                pcm_bytes=chunk_size,
            )
        offset += chunk_size + (chunk_size % 2)
    raise ValueError("payload is missing a data chunk")


def _parse_fmt(payload: bytes) -> WavInfo:
    """Parse a ``fmt `` chunk payload.

    Args:
        payload: The ``fmt `` chunk body.

    Returns:
        The codec/channels/sample rate/bits per sample of the chunk.

    Raises:
        ValueError: When the chunk is malformed or declares an unusable
            PCM layout.
    """
    if len(payload) < _FMT_CHUNK_SIZE:
        raise ValueError("fmt chunk is too short")
    codec, channels, sample_rate, _, _, bits_per_sample = struct.unpack_from(
        "<HHIIHH", payload
    )
    if codec != 1:
        raise ValueError(f"audio codec {codec} is not PCM")
    if channels < 1:
        raise ValueError("audio declares no channels")
    if sample_rate < 1:
        raise ValueError("audio declares an invalid sample rate")
    if bits_per_sample < 1:
        raise ValueError("audio declares an invalid bits-per-sample value")
    return WavInfo(
        codec=codec,
        channels=channels,
        sample_rate=sample_rate,
        bits_per_sample=bits_per_sample,
        pcm_bytes=0,
    )


__all__ = ["WavInfo", "inspect_wav"]