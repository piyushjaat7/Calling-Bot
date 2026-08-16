"""Tests of the TTS service validation and port delegation."""

from __future__ import annotations

import pytest

from backend.app.tts.exceptions import (
    TtsEmptyTextError,
    TtsProviderError,
    TtsTextTooLongError,
)
from backend.app.tts.service import TtsService
from tests.tts.fakes import FakeTtsPort


class TestTtsServiceSynthesis:
    async def test_delegates_to_the_port(self) -> None:
        port = FakeTtsPort()
        service = TtsService(port)
        result = await service.synthesize("Hello, this is Calling Bot.")
        assert result is port.result
        assert port.calls == ["Hello, this is Calling Bot."]

    async def test_provider_error_propagates(self) -> None:
        provider_error = TtsProviderError("engine down")
        service = TtsService(FakeTtsPort(error=provider_error))
        with pytest.raises(TtsProviderError, match="engine down"):
            await service.synthesize("Hello")


class TestTtsServiceValidation:
    async def test_rejects_empty_text(self) -> None:
        port = FakeTtsPort()
        service = TtsService(port)
        with pytest.raises(TtsEmptyTextError, match="empty"):
            await service.synthesize("")
        assert port.calls == []

    async def test_rejects_whitespace_only_text(self) -> None:
        port = FakeTtsPort()
        service = TtsService(port)
        with pytest.raises(TtsEmptyTextError, match="empty"):
            await service.synthesize("   \t\n  ")
        assert port.calls == []

    async def test_rejects_oversized_text(self) -> None:
        port = FakeTtsPort()
        service = TtsService(port, max_text_chars=10)
        with pytest.raises(TtsTextTooLongError, match="10"):
            await service.synthesize("x" * 11)
        assert port.calls == []

    async def test_accepts_text_at_the_limit(self) -> None:
        service = TtsService(FakeTtsPort(), max_text_chars=10)
        result = await service.synthesize("x" * 10)
        assert result is not None

    async def test_rejects_text_with_padding_beyond_the_limit(self) -> None:
        service = TtsService(FakeTtsPort(), max_text_chars=10)
        with pytest.raises(TtsTextTooLongError, match="10"):
            await service.synthesize("   hello   ")