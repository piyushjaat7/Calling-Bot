"""Tests of the TTS WAV header inspector."""

from __future__ import annotations

import struct

import pytest

from backend.app.tts.wav import WavInfo, inspect_wav
from tests.stt.wav_builder import make_wav


def _raw_wav(body: bytes) -> bytes:
    """Build a minimal RIFF/WAVE container around the given chunk bytes."""
    return struct.pack("<4sI4s", b"RIFF", 4 + len(body), b"WAVE") + body


def _fmt_chunk(
    codec: int = 1,
    channels: int = 1,
    sample_rate: int = 16000,
    bits_per_sample: int = 16,
) -> bytes:
    byte_rate: int = sample_rate * channels * bits_per_sample // 8
    return struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        codec,
        channels,
        sample_rate,
        byte_rate,
        channels * bits_per_sample // 8,
        bits_per_sample,
    )


class TestInspectWav:
    def test_parses_valid_wav(self) -> None:
        info: WavInfo = inspect_wav(make_wav(sample_rate=16000))
        assert info == WavInfo(
            codec=1, channels=1, sample_rate=16000, bits_per_sample=16, pcm_bytes=3200
        )

    def test_parses_stereo_and_8_bit(self) -> None:
        audio: bytes = make_wav(channels=2, bits_per_sample=8)
        info: WavInfo = inspect_wav(audio)
        assert info.channels == 2
        assert info.bits_per_sample == 8

    def test_data_chunk_after_extra_chunks(self) -> None:
        audio: bytes = make_wav(extra_chunks=[(b"LIST", b"INFO")])
        info: WavInfo = inspect_wav(audio)
        assert info.sample_rate == 16000
        assert info.pcm_bytes == 3200

    def test_rejects_payload_too_short(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            inspect_wav(b"RIFF")

    def test_rejects_missing_riff_magic(self) -> None:
        with pytest.raises(ValueError, match="RIFF/WAVE"):
            inspect_wav(b"XXXX" + b"\x00" * 40)

    def test_rejects_missing_wave_magic(self) -> None:
        with pytest.raises(ValueError, match="RIFF/WAVE"):
            inspect_wav(b"RIFF" + b"\x00\x00\x00\x00" + b"AVI " + b"\x00" * 40)

    def test_rejects_non_pcm_codec(self) -> None:
        audio: bytes = _raw_wav(_fmt_chunk(codec=6))
        with pytest.raises(ValueError, match="not PCM"):
            inspect_wav(audio)

    def test_rejects_missing_data_chunk(self) -> None:
        audio: bytes = _raw_wav(_fmt_chunk())
        with pytest.raises(ValueError, match="missing a data chunk"):
            inspect_wav(audio)

    def test_reports_empty_data_chunk(self) -> None:
        audio: bytes = make_wav(data=b"")
        info: WavInfo = inspect_wav(audio)
        assert info.pcm_bytes == 0

    def test_rejects_declared_size_beyond_payload(self) -> None:
        audio: bytes = make_wav()[:-16]
        with pytest.raises(ValueError, match="extends beyond"):
            inspect_wav(audio)

    def test_rejects_invalid_fmt_channel_count(self) -> None:
        audio: bytes = _raw_wav(_fmt_chunk(channels=0))
        with pytest.raises(ValueError, match="no channels"):
            inspect_wav(audio)