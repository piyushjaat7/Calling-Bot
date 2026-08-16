"""API tests of the STT router (``POST /stt/transcribe``)."""

from __future__ import annotations

from starlette.testclient import TestClient

from backend.app.stt.exceptions import SttInvalidResponseError, SttProviderError
from backend.app.stt.ports import SttResult
from backend.app.stt.service import SttService
from tests.stt.conftest import make_client
from tests.stt.fakes import FakeSttPort
from tests.stt.wav_builder import make_wav


def _upload(client: TestClient, audio: bytes) -> object:
    return client.post(
        "/stt/transcribe", files={"file": ("sample.wav", audio, "audio/wav")}
    )


class TestTranscribeEndpoint:
    def test_success_returns_transcription(self) -> None:
        service = SttService(FakeSttPort(result=SttResult(text="hello world")))
        with make_client(service) as client:
            response = _upload(client, make_wav())
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Transcription completed.",
            "data": {"text": "hello world"},
        }

    def test_silence_returns_empty_text(self) -> None:
        service = SttService(FakeSttPort(result=SttResult(text="")))
        with make_client(service) as client:
            response = _upload(client, make_wav())
        assert response.status_code == 200
        assert response.json()["data"] == {"text": ""}

    def test_missing_file_field_returns_422(self) -> None:
        service = SttService(FakeSttPort())
        with make_client(service) as client:
            response = client.post("/stt/transcribe")
        assert response.status_code == 422


class TestValidationErrors:
    def test_empty_audio_returns_422(self) -> None:
        service = SttService(FakeSttPort())
        with make_client(service) as client:
            response = _upload(client, b"")
        assert response.status_code == 422

    def test_oversized_audio_returns_413(self) -> None:
        service = SttService(FakeSttPort(), max_audio_bytes=100)
        with make_client(service) as client:
            response = _upload(client, make_wav())
        assert response.status_code == 413

    def test_unsupported_format_returns_415(self) -> None:
        service = SttService(FakeSttPort())
        with make_client(service) as client:
            response = _upload(client, b"definitely not a wav file")
        assert response.status_code == 415

    def test_non_pcm_wav_returns_415(self) -> None:
        service = SttService(FakeSttPort())
        with make_client(service) as client:
            response = _upload(client, make_wav(codec=6))
        assert response.status_code == 415


class TestProviderErrors:
    def test_provider_failure_returns_502(self) -> None:
        service = SttService(FakeSttPort(error=SttProviderError("engine down")))
        with make_client(service) as client:
            response = _upload(client, make_wav())
        assert response.status_code == 502

    def test_invalid_provider_response_returns_502(self) -> None:
        service = SttService(
            FakeSttPort(error=SttInvalidResponseError("bad response"))
        )
        with make_client(service) as client:
            response = _upload(client, make_wav())
        assert response.status_code == 502