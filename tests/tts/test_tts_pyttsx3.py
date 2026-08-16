"""Tests of the Pyttsx3 adapter (fake engine, no real synthesis)."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.tts.exceptions import (
    TtsInvalidOutputError,
    TtsProviderError,
)
from backend.app.tts.ports import TtsPort, TtsResult
from backend.app.tts.pyttsx3 import Pyttsx3Adapter
from tests.stt.wav_builder import make_wav
from tests.tts.fakes import FakePyttsx3Engine


def _make_adapter(
    engine: FakePyttsx3Engine, voice: str | None = None
) -> Pyttsx3Adapter:
    return Pyttsx3Adapter(engine_factory=lambda: engine, voice=voice)


class TestPyttsx3AdapterSuccess:
    async def test_synthesizes_valid_audio(self) -> None:
        audio: bytes = make_wav(sample_rate=16000)
        engine = FakePyttsx3Engine(payload=audio)
        adapter = _make_adapter(engine)

        result: TtsResult = await adapter.synthesize("Hello")

        assert result.audio == audio
        assert result.format == "wav"
        assert result.sample_rate == 16000
        assert result.channels == 1
        assert result.bits_per_sample == 16
        assert result.duration_seconds == pytest.approx(0.1)
        assert engine.ran is True

    async def test_conforms_to_the_port(self) -> None:
        adapter = _make_adapter(FakePyttsx3Engine(payload=make_wav()))
        assert isinstance(adapter, TtsPort)

    async def test_writes_to_a_temp_file_and_cleans_it_up(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav())
        adapter = _make_adapter(engine)
        await adapter.synthesize("Hello")
        assert len(engine.saved_paths) == 1
        assert not Path(engine.saved_paths[0]).exists()

    async def test_applies_configured_voice(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav())
        adapter = _make_adapter(engine, voice="HKEY_LOCAL_MACHINE\\David")
        await adapter.synthesize("Hello")
        assert engine.voice == "HKEY_LOCAL_MACHINE\\David"

    async def test_uses_system_default_voice_when_unconfigured(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav())
        adapter = _make_adapter(engine)
        await adapter.synthesize("Hello")
        assert engine.voice is None

    async def test_initializes_engine_lazily(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav())
        adapter = _make_adapter(engine)
        assert adapter._engine is None
        await adapter.synthesize("Hello")
        assert adapter._engine is engine

    async def test_reports_stereo_output_metadata(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav(channels=2))
        adapter = _make_adapter(engine)
        result: TtsResult = await adapter.synthesize("Hello")
        assert result.channels == 2
        assert result.duration_seconds == pytest.approx(0.1)


class TestPyttsx3AdapterFailures:
    async def test_engine_initialization_failure_is_clean(self) -> None:
        def failing_factory() -> FakePyttsx3Engine:
            raise ValueError("no SAPI5 available")

        adapter = Pyttsx3Adapter(engine_factory=failing_factory)
        with pytest.raises(TtsProviderError, match="initialize"):
            await adapter.synthesize("Hello")

    async def test_save_failure_is_clean(self) -> None:
        engine = FakePyttsx3Engine(
            payload=make_wav(), save_error=RuntimeError("COM error")
        )
        adapter = _make_adapter(engine)
        with pytest.raises(TtsProviderError, match="failed"):
            await adapter.synthesize("Hello")

    async def test_missing_output_file_is_clean(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav(), remove_target=True)
        adapter = _make_adapter(engine)
        with pytest.raises(TtsProviderError, match="no audio file"):
            await adapter.synthesize("Hello")

    async def test_empty_output_file_is_clean(self) -> None:
        engine = FakePyttsx3Engine(payload=None)
        adapter = _make_adapter(engine)
        with pytest.raises(TtsInvalidOutputError, match="invalid"):
            await adapter.synthesize("Hello")

    async def test_garbage_output_is_clean(self) -> None:
        engine = FakePyttsx3Engine(payload=b"definitely not audio")
        adapter = _make_adapter(engine)
        with pytest.raises(TtsInvalidOutputError, match="invalid"):
            await adapter.synthesize("Hello")

    async def test_empty_audio_output_is_clean(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav(data=b""))
        adapter = _make_adapter(engine)
        with pytest.raises(TtsInvalidOutputError, match="no samples"):
            await adapter.synthesize("Hello")

    async def test_non_pcm_output_is_clean(self) -> None:
        engine = FakePyttsx3Engine(payload=make_wav(codec=6))
        adapter = _make_adapter(engine)
        with pytest.raises(TtsInvalidOutputError, match="invalid"):
            await adapter.synthesize("Hello")

    async def test_temp_file_cleaned_up_on_failure(self) -> None:
        engine = FakePyttsx3Engine(payload=b"garbage")
        adapter = _make_adapter(engine)
        with pytest.raises(TtsInvalidOutputError):
            await adapter.synthesize("Hello")
        assert engine.saved_paths
        assert not Path(engine.saved_paths[0]).exists()