"""Tests of the TTS port contract and result model."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from backend.app.tts.ports import TtsPort, TtsResult
from tests.stt.wav_builder import make_wav
from tests.tts.fakes import FakeTtsPort


class TestTtsResult:
    def test_carries_audio_and_metadata(self) -> None:
        audio: bytes = make_wav(sample_rate=22050)
        result = TtsResult(
            audio=audio,
            sample_rate=22050,
            channels=1,
            bits_per_sample=16,
            duration_seconds=0.1,
        )
        assert result.audio == audio
        assert result.sample_rate == 22050
        assert result.channels == 1
        assert result.bits_per_sample == 16
        assert result.duration_seconds == 0.1

    def test_defaults_format_and_duration(self) -> None:
        result = TtsResult(
            audio=make_wav(), sample_rate=16000, channels=1, bits_per_sample=16
        )
        assert result.format == "wav"
        assert result.duration_seconds is None

    def test_is_immutable(self) -> None:
        with pytest.raises(FrozenInstanceError):
            TtsResult(
                audio=make_wav(), sample_rate=16000, channels=1, bits_per_sample=16
            ).format = "mp3"


class TestTtsPortContract:
    async def test_fake_conforms_to_the_port(self) -> None:
        assert isinstance(FakeTtsPort(), TtsPort)

    async def test_returns_configured_result(self) -> None:
        port = FakeTtsPort()
        result = await port.synthesize("hello")
        assert result is port.result

    async def test_reports_calls(self) -> None:
        port = FakeTtsPort()
        await port.synthesize("hello world")
        assert port.calls == ["hello world"]