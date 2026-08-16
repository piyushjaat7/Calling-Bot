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
* :class:`ConversationRepository` — persistence contract of conversations
  and their messages. The engine persists through it when configured;
  without one it falls back to its in-memory registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from backend.app.conversation.context import ConversationContext, SessionView
from backend.app.conversation.conversation import Conversation


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


@runtime_checkable
class ConversationRepository(Protocol):
    """Persistence contract of conversations and their messages.

    The engine persists a conversation through this port after each
    mutation (user message, assistant message, end); it keeps no read
    cache of its own, so the repository must return the full conversation
    with every message, in insertion order. When the engine is created
    without a repository it falls back to its in-memory registry.
    """

    async def get(self, conversation_id: UUID) -> Conversation | None:
        """Return the stored conversation, or ``None`` when unknown.

        Args:
            conversation_id: The conversation to load.

        Returns:
            The hydrated conversation (with every message in sequence
            order) when it exists, ``None`` otherwise.
        """

    async def save(self, conversation: Conversation) -> None:
        """Persist the conversation and every message it holds.

        Idempotent: re-saving the same conversation must not duplicate
        messages or fail on existing rows.

        Args:
            conversation: The conversation to persist.

        Raises:
            Exception: Propagated from the backend when the write fails.
        """


__all__ = ["ConversationRepository", "LlmPort", "LlmResponse", "SessionPort"]