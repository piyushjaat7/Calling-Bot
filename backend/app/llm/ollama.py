"""Ollama adapter — an implementation of the Conversation ``LlmPort``.

Talks to a local Ollama server over its HTTP API (``POST /api/chat``) using
``httpx``: it never shells out to ``ollama run`` and never imports the
``ollama`` client package. The base URL, model and timeout come exclusively
from :class:`~backend.app.config.settings.Settings` (``OLLAMA_BASE_URL``,
``OLLAMA_MODEL``, ``OLLAMA_TIMEOUT_SECONDS``) unless explicitly overridden
at construction time, so nothing here is hardcoded.

All failures are normalized to the clean errors of
:mod:`backend.app.llm.exceptions`; raw ``httpx`` exceptions never escape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import httpx

from backend.app.config.settings import Settings, get_settings
from backend.app.conversation.context import ConversationContext
from backend.app.conversation.ports import LlmPort, LlmResponse
from backend.app.core.logger import (
    LogCategory,
    LogContext,
    bind_context,
    get_category_logger,
)
from backend.app.llm.exceptions import (
    LlmConnectionError,
    LlmHttpError,
    LlmInvalidResponseError,
    LlmTimeoutError,
)

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any

#: Ollama chat endpoint, relative to the configured base URL.
_CHAT_PATH: Final[str] = "/api/chat"

#: Cap applied to provider-provided error text to keep messages small.
_MAX_ERROR_DETAIL_CHARS: Final[int] = 300


class OllamaAdapter(LlmPort):
    """Minimal ``LlmPort`` backed by a local Ollama HTTP server.

    Args:
        base_url: Ollama base URL; defaults to ``OLLAMA_BASE_URL``.
        model: The model to invoke; defaults to ``OLLAMA_MODEL``.
        timeout_seconds: Request timeout in seconds; defaults to
            ``OLLAMA_TIMEOUT_SECONDS``.
        client: Optional pre-configured ``httpx.AsyncClient`` (used by
            tests to inject a mock transport).
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        config: Settings = get_settings()
        self._base_url: str = base_url or config.ollama_base_url
        self._model: str = model or config.ollama_model
        self._timeout_seconds: float = (
            timeout_seconds or config.ollama_timeout_seconds
        )
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(
            base_url=self._base_url
        )
        # The configured timeout is a hard contract of the adapter: it is
        # applied even when an external client was injected.
        self._client.timeout = httpx.Timeout(self._timeout_seconds)
        self._log: Logger = get_category_logger(
            LogCategory.AI, module="llm.ollama"
        )

    async def generate(self, context: ConversationContext) -> LlmResponse:
        """Generate the assistant reply for the given context.

        Args:
            context: The conversation context snapshot to respond to.

        Returns:
            The provider-independent assistant response.

        Raises:
            LlmTimeoutError: When the server exceeds the configured timeout.
            LlmConnectionError: When the server cannot be reached.
            LlmHttpError: When the server responds with a non-success status.
            LlmInvalidResponseError: When the response body is malformed or
                carries no usable text.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in context.messages
            ],
            "stream": False,
        }
        log: Logger = self._log_context(context)
        log.debug(
            f"Calling Ollama model {self._model} with "
            f"{len(payload['messages'])} messages"
        )

        try:
            response: httpx.Response = await self._client.post(
                _CHAT_PATH, json=payload
            )
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError(
                f"Ollama request timed out after {self._timeout_seconds:g}s."
            ) from exc
        except httpx.TransportError as exc:
            raise LlmConnectionError(
                f"Could not reach Ollama at {self._base_url}."
            ) from exc

        if response.status_code != httpx.codes.OK:
            detail: str = self._error_detail(response)
            log.error(f"Ollama returned HTTP {response.status_code}: {detail}")
            raise LlmHttpError(response.status_code, detail)

        content: str | None = self._extract_content(response)
        if content is None or not content.strip():
            log.error("Ollama returned an empty or malformed response")
            raise LlmInvalidResponseError(
                "Ollama returned an empty or malformed response."
            )

        log.info(
            f"Ollama reply received for conversation {context.conversation_id}"
        )
        return LlmResponse(content=content)

    async def aclose(self) -> None:
        """Close the underlying HTTP client (idempotent)."""
        await self._client.aclose()

    # -- Internals -----------------------------------------------------------

    @staticmethod
    def _extract_content(response: httpx.Response) -> str | None:
        """Return the assistant text of a chat response, or ``None``.

        Args:
            response: The raw HTTP response from Ollama.

        Returns:
            The assistant content when present as a string, ``None`` when
            the body is structurally missing it.

        Raises:
            LlmInvalidResponseError: When the body is not valid JSON.
        """
        try:
            data: Any = response.json()
        except ValueError as exc:
            raise LlmInvalidResponseError(
                "Ollama returned a non-JSON response."
            ) from exc
        message: Any = data.get("message") if isinstance(data, dict) else None
        content: Any = message.get("content") if isinstance(message, dict) else None
        return content if isinstance(content, str) else None

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """Extract a sanitized error description from a failed response."""
        try:
            data: Any = response.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("error"), str):
            detail: str = data["error"]
        else:
            detail = response.text
        return (detail or "unknown error").strip()[:_MAX_ERROR_DETAIL_CHARS]

    def _log_context(self, context: ConversationContext) -> Logger:
        """Return the module logger bound with the conversation context."""
        return bind_context(
            self._log,
            LogContext(
                session_id=str(context.session_id),
                provider="ollama",
            ),
        )


__all__ = ["OllamaAdapter"]
