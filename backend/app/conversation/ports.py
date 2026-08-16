"""Conversation Engine external ports.

The engine orchestrates a turn without ever knowing *who* provides the
session facts or the assistant text:

* :class:`SessionPort` — validates that the session referenced by a turn
  exists. Its shape mirrors ``SessionService.get`` from the Session module
  (:meth:`~backend.app.session.service.SessionService.get`) but returns a
  :class:`~backend.app.conversation.context.SessionView` instead of the
  session entity, keeping the Conversation Core free of any Session import.
* :class:`LlmPort` — produces the assistant reply from a conversation
  context. Provider-neutral by construction: no OpenAI/Gemini/Ollama
  vocabulary exists anywhere in this package.
* :class:`LlmResponse` — the provider-independent result type of the LLM
  port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from backend.app.conversation.context import ConversationContext, SessionView


@runtime_checkable
class SessionPort(Protocol):
    """Session lookup contract used by the engine.

    Mirrors the lookup capability of ``SessionService.get`` while exposing
    only a read-only view of the session, never the session entity itself.
    Implementations return ``None`` for unknown sessions.
    """

    async def get(self, session_id: UUID) -> SessionView | None:
        """Return the session view, or ``None`` when the session is unknown.

        Args:
            session_id: The session identifier to look up.

        Returns:
            The session view when the session exists, ``None`` otherwise.
        """


@runtime_checkable
class LlmPort(Protocol):
    """Provider-independent contract of the assistant-text generator."""

    async def generate(self, context: ConversationContext) -> LlmResponse:
        """Generate the assistant reply for the given context.

        Args:
            context: The conversation context snapshot to respond to.

        Returns:
            The provider-independent response.

        Raises:
            Exception: Propagated to the engine when generation fails; the
                port contract does not prescribe a specific error type.
        """


@dataclass(frozen=True, slots=True)
class LlmResponse:
    """Provider-independent result of an :class:`LlmPort` call.

    Attributes:
        content: The assistant reply text.
    """

    content: str


__all__ = ["LlmPort", "LlmResponse", "SessionPort"]