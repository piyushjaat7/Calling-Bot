"""Integration-style test of the full engine -> LLM -> Ollama path.

The Ollama adapter is served by an ``httpx.MockTransport``, so the test
verifies the real ``ConversationEngine -> LlmPort -> OllamaAdapter`` wiring
without requiring a running Ollama server.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from backend.app.conversation.context import SessionView
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.schemas import UserTurn
from backend.app.llm.exceptions import LlmConnectionError
from backend.app.llm.ollama import OllamaAdapter
from tests.conversation.fakes import FakeSessionPort


async def test_engine_turn_flows_through_ollama_adapter() -> None:
    session_id: UUID = uuid4()
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "Hello there."},
                "done": True,
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    adapter = OllamaAdapter(model="llama3:8b", client=client)
    engine = ConversationEngine(
        llm=adapter,
        sessions=FakeSessionPort(
            {session_id: SessionView(session_id=session_id)}
        ),
    )
    try:
        result = await engine.handle_turn(
            UserTurn(session_id=session_id, content="Hello")
        )
    finally:
        await adapter.aclose()

    assert result.assistant_message.content == "Hello there."
    assert result.user_message.content == "Hello"
    assert captured["payload"]["model"] == "llama3:8b"
    assert captured["payload"]["messages"] == [
        {"role": "user", "content": "Hello"}
    ]
    conversation = engine.conversations[0]
    assert [message.content for message in conversation.messages] == [
        "Hello",
        "Hello there.",
    ]


async def test_engine_propagates_clean_llm_errors() -> None:
    session_id: UUID = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    adapter = OllamaAdapter(client=client)
    engine = ConversationEngine(
        llm=adapter,
        sessions=FakeSessionPort(
            {session_id: SessionView(session_id=session_id)}
        ),
    )
    try:
        with pytest.raises(LlmConnectionError):
            await engine.handle_turn(
                UserTurn(session_id=session_id, content="Hello")
            )
    finally:
        await adapter.aclose()