"""Tests of the Vosk adapter, with the vosk API fully faked.

No model, no network and no audio library are involved: the model and
recognizer factories are injected so every success/failure path of the
adapter is deterministic.
"""

from __future__ import annotations

import pytest

from backend.app.config.settings import get_settings
from backend.app.stt.exceptions import (
    SttInvalidResponseError,
    SttProviderError,
)
from backend.app.stt.ports import SttPort, SttResult
from backend.app.stt.vosk import VoskAdapter


class FakeModel:
    """Stand-in for ``vosk.Model``: records the loaded path."""

    def __init__(self, path: str) -> None:
        self.path: str = path


class FakeRecognizer:
    """Stand-in for ``vosk.KaldiRecognizer``: fully scripted."""

    def __init__(
        self,
        model: FakeModel,
        sample_rate: int,
        final_result: str = '{"text": "hello world"}',
        accept_error: Exception | None = None,
    ) -> None:
        self.model: FakeModel = model
        self.sample_rate: int = sample_rate
        self.final_result: str = final_result
        self.accept_error: Exception | None = accept_error
        self.accepted: list[bytes] = []

    def AcceptWaveform(self, pcm: bytes) -> bool:
        if self.accept_error is not None:
            raise self.accept_error
        self.accepted.append(pcm)
        return False

    def FinalResult(self) -> str:
        return self.final_result


@pytest.fixture
def built_model() -> FakeModel:
    """A fake model instance the fake recognizer can hold onto."""
    return FakeModel("unused")


class TestTranscribe:
    async def test_returns_transcription(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(built_model, 16000)
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        result: SttResult = await adapter.transcribe(b"\x00\x01" * 100, 16000)
        assert result == SttResult(text="hello world")

    async def test_feeds_pcm_and_sample_rate(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(built_model, 8000)
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        pcm = b"\x00\x01" * 64
        await adapter.transcribe(pcm, 8000)
        assert recognizer.accepted == [pcm]
        assert recognizer.sample_rate == 8000

    async def test_model_path_defaults_to_settings(
        self, built_model: FakeModel
    ) -> None:
        paths: list[str] = []

        def factory(path: str) -> FakeModel:
            paths.append(path)
            return built_model

        recognizer = FakeRecognizer(built_model, 16000)
        adapter = VoskAdapter(
            model_factory=factory,
            recognizer_factory=lambda model, rate: recognizer,
        )
        await adapter.transcribe(b"\x00" * 4, 16000)
        assert paths == [get_settings().stt_vosk_model_path]

    async def test_model_loaded_once(self, built_model: FakeModel) -> None:
        loads: list[str] = []

        def factory(path: str) -> FakeModel:
            loads.append(path)
            return built_model

        recognizer = FakeRecognizer(built_model, 16000)
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=factory,
            recognizer_factory=lambda model, rate: recognizer,
        )
        await adapter.transcribe(b"\x00" * 4, 16000)
        await adapter.transcribe(b"\x00" * 4, 16000)
        assert len(loads) == 1

    async def test_silence_returns_empty_text(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(built_model, 16000, final_result='{"text": ""}')
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        assert await adapter.transcribe(b"\x00" * 4, 16000) == SttResult(text="")


class TestProviderFailures:
    async def test_model_load_failure_is_clean(self) -> None:
        def factory(_path: str) -> FakeModel:
            raise RuntimeError("missing final.mdl")

        adapter = VoskAdapter(
            model_path="models/missing",
            model_factory=factory,
            recognizer_factory=lambda model, rate: FakeRecognizer(model, rate),
        )
        with pytest.raises(SttProviderError, match="Could not load"):
            await adapter.transcribe(b"\x00" * 4, 16000)

    async def test_recognition_failure_is_clean(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(
            built_model, 16000, accept_error=RuntimeError("crash")
        )
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        with pytest.raises(SttProviderError, match="recognition failed"):
            await adapter.transcribe(b"\x00" * 4, 16000)

    async def test_raw_exceptions_never_leak(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(
            built_model, 16000, accept_error=ValueError("boom")
        )
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        with pytest.raises(SttProviderError):
            await adapter.transcribe(b"\x00" * 4, 16000)


class TestInvalidResponses:
    async def test_non_json_response_rejected(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(built_model, 16000, final_result="not-json")
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        with pytest.raises(SttInvalidResponseError, match="non-JSON"):
            await adapter.transcribe(b"\x00" * 4, 16000)

    async def test_missing_text_field_rejected(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(built_model, 16000, final_result="{}")
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        with pytest.raises(SttInvalidResponseError, match="text"):
            await adapter.transcribe(b"\x00" * 4, 16000)

    async def test_non_string_text_rejected(self, built_model: FakeModel) -> None:
        recognizer = FakeRecognizer(
            built_model, 16000, final_result='{"text": 42}'
        )
        adapter = VoskAdapter(
            model_path="models/fake",
            model_factory=lambda _path: built_model,
            recognizer_factory=lambda model, rate: recognizer,
        )
        with pytest.raises(SttInvalidResponseError, match="text"):
            await adapter.transcribe(b"\x00" * 4, 16000)


class TestPortContract:
    def test_adapter_conforms_to_the_port(self) -> None:
        assert isinstance(VoskAdapter(), SttPort)