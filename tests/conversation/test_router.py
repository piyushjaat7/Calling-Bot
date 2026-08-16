"""End-to-end tests of the conversation REST endpoints.

The router is mounted directly on a throwaway FastAPI application with the
engine dependency overridden by a fake-ports engine, so no Ollama server or
session service is involved. The error translation of the HTTP layer is
exercised against every engine failure mode.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.app.conversation.context import SessionView
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.router import get_conversation_engine, router
from backend.app.llm.exceptions import LlmConnectionError
from tests.conversation.fakes import FakeLlmPort, FakeSessionPort


@pytest.fixture
def session_id() -> UUID:
    """A session identifier known to the fake session port."""
    return uuid4()


@pytest.fixture
def other_session_id() -> UUID:
    """A second session identifier known to the fake session port."""
    return uuid4()


@pytest.fixture
def fake_llm() -> FakeLlmPort:
    """A fake LLM port returning a fixed assistant response."""
    return FakeLlmPort()


@pytest.fixture
def engine(
    session_id: UUID, other_session_id: UUID, fake_llm: FakeLlmPort
) -> ConversationEngine:
    """An engine wired to the fake ports (no Ollama involved)."""
    return ConversationEngine(
        llm=fake_llm,
        sessions=FakeSessionPort(
            {
                session_id: SessionView(session_id=session_id),
                other_session_id: SessionView(session_id=other_session_id),
            }
        ),
    )


@pytest.fixture
def client(engine: ConversationEngine) -> Iterator[TestClient]:
    """A TestClient mounting the conversation router with the fake engine."""
    app = FastAPI()
    app.dependency_overrides[get_conversation_engine] = lambda: engine
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client


def _turn_payload(
    session_id: UUID, content: str = "Hello", conversation_id: UUID | None = None
) -> dict[str, str]:
    """Build a valid turn payload, optionally continuing a conversation."""
    payload: dict[str, str] = {
        "session_id": str(session_id),
        "content": content,
    }
    if conversation_id is not None:
        payload["conversation_id"] = str(conversation_id)
    return payload


class TestTurnEndpoint:
    def test_valid_turn_returns_assistant_response(
        self, client: TestClient, session_id: UUID
    ) -> None:
        response = client.post("/conversation/turn", json=_turn_payload(session_id))
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["message"] == "Turn processed."
        data = payload["data"]
        assert data["session_id"] == str(session_id)
        assert UUID(data["conversation_id"]).version == 4
        assert data["state"] == "active"
        assert data["turn_count"] == 1
        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "Hello"
        assert data["user_message"]["sequence"] == 0
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["content"] == "Hello there."
        assert data["assistant_message"]["sequence"] == 1

    def test_turn_continues_existing_conversation(
        self, client: TestClient, session_id: UUID
    ) -> None:
        first = client.post("/conversation/turn", json=_turn_payload(session_id))
        conversation_id = first.json()["data"]["conversation_id"]
        second = client.post(
            "/conversation/turn",
            json=_turn_payload(session_id, content="again", conversation_id=conversation_id),
        )
        assert second.status_code == 200
        data = second.json()["data"]
        assert data["conversation_id"] == conversation_id
        assert data["turn_count"] == 2
        assert data["user_message"]["sequence"] == 2
        assert data["assistant_message"]["sequence"] == 3

    def test_missing_session_returns_404(self, client: TestClient) -> None:
        response = client.post(
            "/conversation/turn", json=_turn_payload(uuid4())
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_missing_conversation_returns_404(
        self, client: TestClient, session_id: UUID
    ) -> None:
        response = client.post(
            "/conversation/turn",
            json=_turn_payload(session_id, conversation_id=uuid4()),
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_conversation_of_another_session_returns_409(
        self, client: TestClient, session_id: UUID, other_session_id: UUID
    ) -> None:
        first = client.post("/conversation/turn", json=_turn_payload(session_id))
        conversation_id = first.json()["data"]["conversation_id"]
        response = client.post(
            "/conversation/turn",
            json=_turn_payload(other_session_id, conversation_id=conversation_id),
        )
        assert response.status_code == 409
        assert "does not belong" in response.json()["detail"]

    async def test_ended_conversation_returns_409(
        self, client: TestClient, engine: ConversationEngine, session_id: UUID
    ) -> None:
        first = client.post("/conversation/turn", json=_turn_payload(session_id))
        conversation_id = first.json()["data"]["conversation_id"]
        await engine.end(UUID(conversation_id))
        response = client.post(
            "/conversation/turn",
            json=_turn_payload(
                session_id, content="Late message", conversation_id=conversation_id
            ),
        )
        assert response.status_code == 409
        assert "already ended" in response.json()["detail"]


class TestInvalidRequests:
    def test_missing_session_id_returns_422(self, client: TestClient) -> None:
        response = client.post("/conversation/turn", json={"content": "Hello"})
        assert response.status_code == 422

    def test_invalid_session_id_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/conversation/turn", json={"session_id": "not-a-uuid", "content": "Hello"}
        )
        assert response.status_code == 422

    def test_empty_content_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/conversation/turn", json={"session_id": str(uuid4()), "content": ""}
        )
        assert response.status_code == 422

    def test_blank_content_returns_422(
        self, client: TestClient, session_id: UUID
    ) -> None:
        response = client.post(
            "/conversation/turn",
            json={"session_id": str(session_id), "content": "   "},
        )
        assert response.status_code == 422

    def test_extra_field_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/conversation/turn",
            json={"session_id": str(uuid4()), "content": "Hi", "extra": True},
        )
        assert response.status_code == 422


class TestLlmFailure:
    def test_llm_failure_translated_to_502(
        self, client: TestClient, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        fake_llm.error = LlmConnectionError(
            "Could not reach Ollama at http://localhost:11434."
        )
        response = client.post("/conversation/turn", json=_turn_payload(session_id))
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "Could not reach Ollama" in detail
        assert "ConnectError" not in detail