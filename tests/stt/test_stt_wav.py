"""Tests of the WAV container parsing used by the STT service."""

from __future__ import annotations

import pytest

from backend.app.stt.wav import parse_wav
from tests.stt.wav_builder import make_wav


class TestParseWav:
    def test_valid_wav_returns_rate_and_pcm(self) -> None:
        rate, pcm = parse_wav(make_wav(sample_rate=16000))
        assert rate == 16000
        assert len(pcm) == 3200

    def test_pcm_payload_preserved_verbatim(self) -> None:
        payload = b"\x01\x00" * 100
        rate, pcm = parse_wav(make_wav(data=payload))
        assert rate == 16000
        assert pcm == payload

    def test_rate_read_from_header(self) -> None:
        rate, _ = parse_wav(make_wav(sample_rate=8000))
        assert rate == 8000

    def test_extra_chunks_before_data_tolerated(self) -> None:
        rate, pcm = parse_wav(
            make_wav(
                sample_rate=16000,
                extra_chunks=[(b"LIST", b"\x00" * 6), (b"fact", b"\x04\x00\x00\x00")],
            )
        )
        assert rate == 16000
        assert len(pcm) == 3200

    def test_too_short_rejected(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            parse_wav(b"\x00" * 20)

    def test_missing_riff_magic_rejected(self) -> None:
        audio = make_wav()
        with pytest.raises(ValueError, match="RIFF/WAVE"):
            parse_wav(b"XXXX" + audio[4:])

    def test_missing_wave_magic_rejected(self) -> None:
        audio = bytearray(make_wav())
        audio[8:12] = b"FAIL"
        with pytest.raises(ValueError, match="RIFF/WAVE"):
            parse_wav(bytes(audio))

    def test_non_pcm_codec_rejected(self) -> None:
        with pytest.raises(ValueError, match="codec"):
            parse_wav(make_wav(codec=6))

    def test_stereo_rejected(self) -> None:
        with pytest.raises(ValueError, match="mono"):
            parse_wav(make_wav(channels=2))

    def test_8_bit_rejected(self) -> None:
        with pytest.raises(ValueError, match="16-bit"):
            parse_wav(make_wav(bits_per_sample=8))

    def test_sample_rate_out_of_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="sample rate"):
            parse_wav(make_wav(sample_rate=6000))

    def test_missing_data_chunk_rejected(self) -> None:
        audio = make_wav(extra_chunks=[(b"LIST", b"\x00" * 6)])
        truncated = audio[: audio.find(b"data")]
        assert len(truncated) >= 44
        with pytest.raises(ValueError, match="no data chunk"):
            parse_wav(truncated)

    def test_empty_data_chunk_rejected(self) -> None:
        with pytest.raises(ValueError, match="no audio data"):
            parse_wav(make_wav(data=b""))