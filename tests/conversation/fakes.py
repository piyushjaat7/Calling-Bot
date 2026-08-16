"""Fake implementations of the Conversation Engine ports.

Duck-typed :class:`~backend.app.conversation.ports.SessionPort` and
:class:`~backend.app.conversation.ports.LlmPort` implementations used across
the Conversation Engine tests: no persistence, no provider, fully scripted.
"""

from __future__ import annotations

from uuid import UUID

from backend.app.conversation.context import ConversationContext, SessionView
from backend.app.conversation.ports import LlmResponse


class FakeSessionPort:
    """SessionPort backed by a configured dictionary of session views."""

    def __init__(self, sessions: dict[UUID, SessionView] | None = None) -> None:
        self.sessions: dict[UUID, SessionView] = dict(sessions or {})
        self.lookups: list[UUID] = []

    async def get(self, session_id: UUID) -> SessionView | None:
        """Record the lookup and return the configured view (or ``None``)."""
        self.lookups.append(session_id)
        return self.sessions.get(session_id)


class FakeLlmPort:
    """LlmPort returning a fixed response or raising a configured error."""

    def __init__(self, response: str = "Hello there.") -> None:
        self.response: str = response
        self.error: Exception | None = None
        self.calls: list[ConversationContext] = []

    async def generate(self, context: ConversationContext) -> LlmResponse:
        """Record the context and return the response (or raise the error)."""
        self.calls.append(context)
        if self.error is not None:
            raise self.error
        return LlmResponse(content=self.response)