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
from tests.conversation.fakes import FakeLlmPort


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient around the real application factory.

    The production defaults (PostgreSQL-backed repositories) are replaced
    with in-memory instances so the suite runs without a database server;
    the application-level wiring (lifespan, routers) is exercised as-is.
    """
    app = create_app()
    repository = SessionInMemoryRepository()
    service = SessionService(repository)
    engine = ConversationEngine(
        llm=FakeLlmPort(),
        sessions=ServiceSessionPort(service),
    )
    app.dependency_overrides[get_session_service] = lambda: service
    app.dependency_overrides[get_conversation_engine] = lambda: engine
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