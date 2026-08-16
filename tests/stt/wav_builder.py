"""Builder of minimal WAV payloads for the STT tests.

Produces structurally valid (or deliberately broken) RIFF/WAVE files
without any audio library: 16-bit mono PCM silence by default, with knobs
to exercise every validation rule of the STT service.
"""

from __future__ import annotations

import struct


def make_wav(
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16,
    codec: int = 1,
    data: bytes | None = None,
    extra_chunks: list[tuple[bytes, bytes]] | None = None,
) -> bytes:
    """Build a WAV file around the given payload.

    Args:
        sample_rate: Sample rate in Hz (default 16 kHz).
        channels: Number of channels (default mono).
        bits_per_sample: Bits per sample (default 16).
        codec: ``fmt `` audio format code (default 1 = PCM).
        data: The PCM payload; defaults to 0.1 s of silence.
        extra_chunks: Optional ``(chunk_id, payload)`` pairs inserted
            before the ``data`` chunk (e.g. a ``LIST`` chunk).

    Returns:
        The complete WAV file bytes.
    """
    pcm: bytes = (
        data
        if data is not None
        else bytes(sample_rate * channels * bits_per_sample // 8 // 10)
    )
    byte_rate: int = sample_rate * channels * bits_per_sample // 8
    block_align: int = channels * bits_per_sample // 8

    fmt_chunk: bytes = struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        codec,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    body: bytes = b"".join(
        [fmt_chunk]
        + [
            struct.pack("<4sI", chunk_id, len(payload)) + payload
            for chunk_id, payload in (extra_chunks or [])
        ]
        + [struct.pack("<4sI", b"data", len(pcm)), pcm]
    )
    return struct.pack("<4sI4s", b"RIFF", 4 + len(body), b"WAVE") + body