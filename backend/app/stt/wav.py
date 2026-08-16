"""WAV container parsing for the MVP audio input format.

The STT service accepts 16-bit mono PCM inside a RIFF/WAVE container — the
practical input of any telephony-adjacent pipeline and the native format of
the Vosk recognizer. This module extracts the PCM payload and its sample
rate from the header, tolerating extra chunks (``LIST``, ``fact``, ...)
that commonly precede the ``data`` chunk.

Format contract enforced here:

* RIFF/WAVE magic,
* PCM codec (format code 1),
* mono (1 channel),
* 16-bit samples,
* sample rate between 8 kHz and 48 kHz,
* a ``data`` chunk carrying at least one byte.
"""

from __future__ import annotations

#: Minimum size of a RIFF header with a ``fmt `` and a ``data`` chunk.
_MIN_WAV_BYTES: int = 44

#: PCM codec identifier of the ``fmt `` chunk.
_PCM_FORMAT: int = 1

#: Supported sample-rate range (Hz) of the MVP format.
_MIN_SAMPLE_RATE: int = 8000
_MAX_SAMPLE_RATE: int = 48000

#: Chunks are word-aligned (pad byte after odd-sized payloads).
_CHUNK_ALIGNMENT: int = 2


def parse_wav(audio: bytes) -> tuple[int, bytes]:
    """Extract the PCM payload and sample rate of a validated WAV upload.

    Args:
        audio: The full WAV file bytes.

    Returns:
        A tuple of ``(sample_rate, pcm)`` where ``pcm`` is the raw 16-bit
        mono little-endian payload of the ``data`` chunk.

    Raises:
        ValueError: When the bytes are structurally not a supported WAV
            file (wrong magic, non-PCM codec, non-mono, non-16-bit,
            unsupported sample rate, missing/empty ``data`` chunk).
    """
    if len(audio) < _MIN_WAV_BYTES:
        raise ValueError("audio is too short to be a WAV file")
    if audio[0:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise ValueError("audio is not a RIFF/WAVE file")

    audio_format: int = int.from_bytes(audio[20:22], "little")
    if audio_format != _PCM_FORMAT:
        raise ValueError(f"unsupported WAV codec {audio_format} (PCM expected)")

    channels: int = int.from_bytes(audio[22:24], "little")
    if channels != 1:
        raise ValueError(f"expected mono audio, got {channels} channels")

    sample_rate: int = int.from_bytes(audio[24:28], "little")
    if not (_MIN_SAMPLE_RATE <= sample_rate <= _MAX_SAMPLE_RATE):
        raise ValueError(
            f"sample rate {sample_rate} Hz is outside the supported "
            f"{_MIN_SAMPLE_RATE}-{_MAX_SAMPLE_RATE} Hz range"
        )

    bits_per_sample: int = int.from_bytes(audio[34:36], "little")
    if bits_per_sample != 16:
        raise ValueError(f"expected 16-bit PCM, got {bits_per_sample} bits")

    offset: int = 12
    while offset + 8 <= len(audio):
        chunk_id: bytes = audio[offset : offset + 4]
        chunk_size: int = int.from_bytes(audio[offset + 4 : offset + 8], "little")
        payload_start: int = offset + 8
        if chunk_id == b"data":
            pcm: bytes = audio[payload_start : payload_start + chunk_size]
            if not pcm:
                raise ValueError("WAV file contains no audio data")
            return sample_rate, pcm
        offset = payload_start + chunk_size + (chunk_size % _CHUNK_ALIGNMENT)

    raise ValueError("WAV file has no data chunk")


__all__ = ["parse_wav"]