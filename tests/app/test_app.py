"""Application-level API tests.

Verifies that :func:`backend.app.app.create_app` boots the full application:
health, session and conversation routers are mounted, and the whole
``HTTP -> FastAPI -> Conversation Router -> ConversationEngine -> LlmPort``
path works end-to-end. The LLM port is faked here — the real Ollama adapter
is covered by its own test suite and never runs against a server.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from backend.app.app import create_app
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.router import get_conversation_engine
from backend.app.session.repository import SessionInMemoryRepository
from backend.app.session.router import get_session_service
from backend.app.session.service import SessionService
from backend.app.session.session_port import ServiceSessionPort
from backend.app.stt.ports import SttResult
from backend.app.stt.router import get_stt_service
from backend.app.stt.service import SttService
from tests.conversation.fakes import FakeLlmPort
from tests.stt.fakes import FakeSttPort
from tests.stt.wav_builder import make_wav


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient around the real application factory.

    The production defaults (PostgreSQL-backed repositories, local STT
    model) are replaced with in-memory/fake instances so the suite runs
    without a database or a speech model; the application-level wiring
    (lifespan, routers) is exercised as-is.
    """
    app = create_app()
    repository = SessionInMemoryRepository()
    service = SessionService(repository)
    engine = ConversationEngine(
        llm=FakeLlmPort(),
        sessions=ServiceSessionPort(service),
    )
    stt_service = SttService(FakeSttPort(result=SttResult(text="hello world")))
    app.dependency_overrides[get_session_service] = lambda: service
    app.dependency_overrides[get_conversation_engine] = lambda: engine
    app.dependency_overrides[get_stt_service] = lambda: stt_service
    with TestClient(app) as test_client:
        yield test_client


class TestApplicationBoot:
    def test_application_starts(self, client: TestClient) -> None:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    def test_health_endpoint(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Backend is healthy.",
            "data": {"status": "ok"},
        }

    def test_session_router_is_mounted(self, client: TestClient) -> None:
        response = client.post("/session/start")
        assert response.status_code == 201
        assert response.json()["data"]["status"] == "active"

    def test_conversation_router_is_mounted(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/conversation/turn" in paths
        assert "/session/start" in paths
        assert "/session/end" in paths
        assert "/session/{session_id}" in paths

    def test_stt_router_is_mounted(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/stt/transcribe" in paths


class TestSttFlow:
    def test_full_transcription_flow_http_to_fake_port(self) -> None:
        """HTTP -> FastAPI -> STT router -> service -> fake port -> text."""
        stt_service = SttService(FakeSttPort(result=SttResult(text="hello world")))
        app = create_app()
        app.dependency_overrides[get_stt_service] = lambda: stt_service

        with TestClient(app) as test_client:
            response = test_client.post(
                "/stt/transcribe",
                files={"file": ("sample.wav", make_wav(), "audio/wav")},
            )
            assert response.status_code == 200
            assert response.json()["data"] == {"text": "hello world"}


class TestApplicationFlow:
    def test_full_turn_flow_http_to_fake_llm(self) -> None:
        """HTTP -> FastAPI -> router -> engine -> fake LlmPort -> reply."""
        repository = SessionInMemoryRepository()
        service = SessionService(repository)
        engine = ConversationEngine(
            llm=FakeLlmPort(),
            sessions=ServiceSessionPort(service),
        )
        app = create_app()
        app.dependency_overrides[get_session_service] = lambda: service
        app.dependency_overrides[get_conversation_engine] = lambda: engine

        with TestClient(app) as test_client:
            started = test_client.post("/session/start")
            assert started.status_code == 201
            session_id = started.json()["data"]["session_id"]

            turn = test_client.post(
                "/conversation/turn",
                json={"session_id": session_id, "content": "Hello"},
            )
            assert turn.status_code == 200
            data = turn.json()["data"]
            assert data["state"] == "active"
            assert data["user_message"]["content"] == "Hello"
            assert data["assistant_message"]["content"] == "Hello there."

            again = test_client.post(
                "/conversation/turn",
                json={
                    "session_id": session_id,
                    "conversation_id": data["conversation_id"],
                    "content": "Again",
                },
            )
            assert again.status_code == 200
            assert again.json()["data"]["turn_count"] == 2
            assert again.json()["data"]["user_message"]["sequence"] == 2
            assert again.json()["data"]["assistant_message"]["sequence"] == 3

            missing = test_client.post(
                "/conversation/turn",
                json={"session_id": "00000000-0000-0000-0000-000000000000", "content": "Hi"},
            )
            assert missing.status_code == 404