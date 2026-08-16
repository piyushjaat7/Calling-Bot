"""Tests of the STT service (validation boundary + delegation)."""

from __future__ import annotations

import pytest

from backend.app.stt.exceptions import (
    SttAudioTooLargeError,
    SttEmptyAudioError,
    SttProviderError,
    SttUnsupportedFormatError,
)
from backend.app.stt.ports import SttResult
from backend.app.stt.service import SttService
from tests.stt.fakes import FakeSttPort
from tests.stt.wav_builder import make_wav


class TestTranscribe:
    async def test_success_delegates_to_port(self) -> None:
        port = FakeSttPort(result=SttResult(text="hello world"))
        service = SttService(port)
        audio = make_wav(sample_rate=16000)
        result = await service.transcribe(audio)
        assert result == SttResult(text="hello world")

    async def test_port_receives_decoded_pcm_and_rate(self) -> None:
        port = FakeSttPort(result=SttResult(text="hello"))
        service = SttService(port)
        payload = b"\x00\x01" * 100
        await service.transcribe(make_wav(sample_rate=8000, data=payload))
        assert port.calls == [(payload, 8000)]

    async def test_provider_error_propagates(self) -> None:
        port = FakeSttPort(error=SttProviderError("engine down"))
        service = SttService(port)
        with pytest.raises(SttProviderError, match="engine down"):
            await service.transcribe(make_wav())


class TestValidation:
    async def test_empty_audio_rejected(self) -> None:
        service = SttService(FakeSttPort())
        with pytest.raises(SttEmptyAudioError, match="empty"):
            await service.transcribe(b"")

    async def test_oversized_audio_rejected(self) -> None:
        service = SttService(FakeSttPort(), max_audio_bytes=100)
        with pytest.raises(SttAudioTooLargeError, match="100 bytes"):
            await service.transcribe(make_wav())

    async def test_undersized_audio_accepted(self) -> None:
        port = FakeSttPort(result=SttResult(text="ok"))
        service = SttService(port, max_audio_bytes=100)
        result = await service.transcribe(make_wav(data=b"\x00\x00"))
        assert result == SttResult(text="ok")

    async def test_garbage_audio_rejected(self) -> None:
        service = SttService(FakeSttPort())
        with pytest.raises(SttUnsupportedFormatError, match="Unsupported audio"):
            await service.transcribe(b"this is not audio at all")

    async def test_non_pcm_wav_rejected(self) -> None:
        service = SttService(FakeSttPort())
        with pytest.raises(SttUnsupportedFormatError, match="codec"):
            await service.transcribe(make_wav(codec=6))

    async def test_empty_audio_never_reaches_port(self) -> None:
        port = FakeSttPort()
        service = SttService(port)
        with pytest.raises(SttEmptyAudioError):
            await service.transcribe(b"")
        assert port.calls == []