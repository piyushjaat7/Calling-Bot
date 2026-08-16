"""Tests of the TTS REST endpoint."""

from __future__ import annotations

import base64

import pytest
from starlette.testclient import TestClient

from backend.app.tts.exceptions import (
    TtsInvalidOutputError,
    TtsProviderError,
)
from backend.app.tts.service import TtsService
from tests.stt.wav_builder import make_wav
from tests.tts.conftest import make_client
from tests.tts.fakes import FakeTtsPort

_AUDIO: bytes = make_wav()


class TestSynthesizeSuccess:
    def test_returns_audio_envelope(self, client: TestClient) -> None:
        response = client.post("/tts/synthesize", json={"text": "Hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Speech synthesized."
        data = body["data"]
        assert data["format"] == "wav"
        assert data["sample_rate"] == 16000
        assert data["channels"] == 1
        assert data["bits_per_sample"] == 16
        assert data["duration_seconds"] == pytest.approx(0.1)
        assert data["size_bytes"] == len(_AUDIO)
        assert base64.b64decode(data["audio_base64"]) == _AUDIO

    def test_returns_verifiable_wav_audio(self, client: TestClient) -> None:
        response = client.post("/tts/synthesize", json={"text": "Hello"})
        audio: bytes = base64.b64decode(response.json()["data"]["audio_base64"])
        assert audio[:4] == b"RIFF"
        assert audio[8:12] == b"WAVE"


class TestSynthesizeValidation:
    def test_missing_text_field_is_rejected(self, client: TestClient) -> None:
        assert client.post("/tts/synthesize", json={}).status_code == 422

    def test_non_string_text_is_rejected(self, client: TestClient) -> None:
        response = client.post("/tts/synthesize", json={"text": 42})
        assert response.status_code == 422

    def test_extra_field_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/tts/synthesize", json={"text": "Hello", "rate": 1.5}
        )
        assert response.status_code == 422

    def test_empty_text_is_rejected(self, client: TestClient) -> None:
        response = client.post("/tts/synthesize", json={"text": ""})
        assert response.status_code == 422
        assert "empty" in response.json()["detail"]

    def test_whitespace_only_text_is_rejected(self, client: TestClient) -> None:
        response = client.post("/tts/synthesize", json={"text": "   \t "})
        assert response.status_code == 422
        assert "empty" in response.json()["detail"]

    def test_oversized_text_is_rejected(self) -> None:
        service = TtsService(FakeTtsPort(), max_text_chars=10)
        with make_client(service) as test_client:
            response = test_client.post(
                "/tts/synthesize", json={"text": "x" * 11}
            )
        assert response.status_code == 422
        assert "10" in response.json()["detail"]


class TestSynthesizeFailures:
    def test_provider_failure_is_mapped_to_502(self) -> None:
        service = TtsService(
            FakeTtsPort(error=TtsProviderError("engine down"))
        )
        with make_client(service) as test_client:
            response = test_client.post("/tts/synthesize", json={"text": "Hello"})
        assert response.status_code == 502
        assert response.json()["detail"] == "engine down"

    def test_invalid_provider_output_is_mapped_to_502(self) -> None:
        service = TtsService(
            FakeTtsPort(error=TtsInvalidOutputError("Synthesized audio is invalid."))
        )
        with make_client(service) as test_client:
            response = test_client.post("/tts/synthesize", json={"text": "Hello"})
        assert response.status_code == 502

    def test_invalid_text_never_reaches_the_port(self) -> None:
        port = FakeTtsPort()
        service = TtsService(port)
        with make_client(service) as test_client:
            response = test_client.post("/tts/synthesize", json={"text": "  "})
        assert response.status_code == 422
        assert port.calls == []