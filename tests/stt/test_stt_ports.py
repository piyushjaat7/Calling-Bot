"""Tests of the STT port contract and result model."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from backend.app.stt.ports import SttPort, SttResult
from tests.stt.fakes import FakeSttPort


class TestSttResult:
    def test_holds_text(self) -> None:
        result = SttResult(text="hello world")
        assert result.text == "hello world"

    def test_holds_empty_text_for_silence(self) -> None:
        assert SttResult(text="").text == ""

    def test_is_immutable(self) -> None:
        with pytest.raises(FrozenInstanceError):
            SttResult(text="x").text = "y"


class TestSttPortContract:
    async def test_fake_conforms_to_the_port(self) -> None:
        assert isinstance(FakeSttPort(), SttPort)

    async def test_returns_configured_result(self) -> None:
        port = FakeSttPort(result=SttResult(text="hello"))
        assert await port.transcribe(b"\x00\x01", 16000) == SttResult(text="hello")

    async def test_reports_calls(self) -> None:
        port = FakeSttPort(result=SttResult(text="hello"))
        await port.transcribe(b"\x00\x01", 8000)
        assert port.calls == [(b"\x00\x01", 8000)]