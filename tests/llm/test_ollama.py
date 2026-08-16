"""Unit tests of the Ollama adapter with a mocked HTTP transport.

No real Ollama server is involved: every request is served by an
``httpx.MockTransport`` handler installed on the injected client, which also
makes the tests deterministic and fast.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest

from backend.app.config.settings import get_settings
from backend.app.conversation.context import (
    ConversationContext,
    SessionView,
    build_context,
)
from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import MessageRole
from backend.app.conversation.ports import LlmResponse
from backend.app.llm.exceptions import (
    LlmConnectionError,
    LlmError,
    LlmHttpError,
    LlmInvalidResponseError,
    LlmTimeoutError,
)
from backend.app.llm.ollama import OllamaAdapter

_BASE_URL: str = "http://ollama.test"
_MODEL: str = "llama3:8b"

Handler = Callable[[httpx.Request], httpx.Response]


def make_context(*pairs: tuple[MessageRole, str]) -> ConversationContext:
    """Build a context from ``(role, content)`` pairs."""
    conversation = Conversation(session_id=uuid4())
    for role, content in pairs:
        conversation.add_message(role, content)
    return build_context(
        conversation, session=SessionView(session_id=conversation.session_id)
    )


def make_adapter(
    handler: Handler,
    *,
    base_url: str = _BASE_URL,
    model: str = _MODEL,
    timeout_seconds: float = 30.0,
) -> OllamaAdapter:
    """Build an adapter whose requests are served by ``handler``."""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=base_url
    )
    return OllamaAdapter(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        client=client,
    )


def _ok_response(content: str) -> httpx.Response:
    """A structurally valid Ollama chat response."""
    return httpx.Response(
        200,
        json={
            "model": _MODEL,
            "message": {"role": "assistant", "content": content},
            "done": True,
        },
    )


class TestSuccessfulGeneration:
    async def test_returns_assistant_content(self) -> None:
        adapter = make_adapter(lambda request: _ok_response("Hello there!"))

        try:
            result = await adapter.generate(
                make_context((MessageRole.USER, "Hi"))
            )
        finally:
            await adapter.aclose()

        assert isinstance(result, LlmResponse)
        assert result.content == "Hello there!"

    async def test_sends_expected_payload(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["payload"] = json.loads(request.content)
            return _ok_response("ok")

        adapter = make_adapter(handler)
        try:
            await adapter.generate(
                make_context(
                    (MessageRole.USER, "one"),
                    (MessageRole.ASSISTANT, "two"),
                    (MessageRole.USER, "three"),
                )
            )
        finally:
            await adapter.aclose()

        assert captured["url"] == f"{_BASE_URL}/api/chat"
        assert captured["payload"] == {
            "model": _MODEL,
            "messages": [
                {"role": "user", "content": "one"},
                {"role": "assistant", "content": "two"},
                {"role": "user", "content": "three"},
            ],
            "stream": False,
        }


class TestConfiguration:
    async def test_defaults_come_from_settings(self) -> None:
        config = get_settings()
        adapter = OllamaAdapter()
        try:
            assert adapter._base_url == config.ollama_base_url
            assert adapter._model == config.ollama_model
            assert adapter._timeout_seconds == config.ollama_timeout_seconds
        finally:
            await adapter.aclose()

    async def test_explicit_values_override_settings(self) -> None:
        adapter = OllamaAdapter(
            base_url="http://ollama.test:11434",
            model="llama3:8b",
            timeout_seconds=42.0,
        )
        try:
            assert adapter._base_url == "http://ollama.test:11434"
            assert adapter._model == "llama3:8b"
            assert adapter._timeout_seconds == 42.0
            assert adapter._client.timeout.read == 42.0
        finally:
            await adapter.aclose()

    async def test_uses_configured_base_url_model_and_timeout(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["payload"] = json.loads(request.content)
            return _ok_response("ok")

        adapter = make_adapter(
            handler,
            base_url="http://ollama.test:11434",
            model="llama3:8b",
            timeout_seconds=42.0,
        )
        try:
            await adapter.generate(make_context((MessageRole.USER, "Hi")))
        finally:
            await adapter.aclose()

        assert captured["url"] == "http://ollama.test:11434/api/chat"
        assert captured["payload"]["model"] == "llama3:8b"
        assert adapter._client.timeout.read == 42.0


class TestFailureModes:
    async def test_timeout_raises_clean_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out", request=request)

        adapter = make_adapter(handler)
        try:
            with pytest.raises(LlmTimeoutError, match="timed out"):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_connection_failure_raises_clean_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        adapter = make_adapter(handler)
        try:
            with pytest.raises(LlmConnectionError, match="Could not reach"):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_http_error_raises_clean_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                404, json={"error": "model 'llama3:8b' not found"}
            )

        adapter = make_adapter(handler)
        try:
            with pytest.raises(LlmHttpError) as excinfo:
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

        assert excinfo.value.status_code == 404
        assert "not found" in excinfo.value.detail

    async def test_http_error_with_non_json_body(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal server error")

        adapter = make_adapter(handler)
        try:
            with pytest.raises(LlmHttpError) as excinfo:
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

        assert excinfo.value.status_code == 500
        assert "internal server error" in excinfo.value.detail

    async def test_empty_content_raises(self) -> None:
        adapter = make_adapter(lambda request: _ok_response(""))
        try:
            with pytest.raises(LlmInvalidResponseError):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_blank_content_raises(self) -> None:
        adapter = make_adapter(lambda request: _ok_response("   \t "))
        try:
            with pytest.raises(LlmInvalidResponseError):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_missing_message_field_raises(self) -> None:
        adapter = make_adapter(
            lambda request: httpx.Response(200, json={"done": True})
        )
        try:
            with pytest.raises(LlmInvalidResponseError):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_non_json_body_raises(self) -> None:
        adapter = make_adapter(
            lambda request: httpx.Response(200, text="<html>boom</html>")
        )
        try:
            with pytest.raises(LlmInvalidResponseError):
                await adapter.generate(
                    make_context((MessageRole.USER, "Hi"))
                )
        finally:
            await adapter.aclose()

    async def test_raw_exceptions_never_leak(self) -> None:
        """Every failure mode surfaces as a clean ``LlmError`` subclass."""

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out", request=request)

        def connect_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        for handler in (timeout_handler, connect_handler):
            adapter = make_adapter(handler)
            try:
                with pytest.raises(LlmError):
                    await adapter.generate(
                        make_context((MessageRole.USER, "Hi"))
                    )
            finally:
                await adapter.aclose()
