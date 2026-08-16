"""Conversation Engine schemas.

:class:`UserTurn` is the validated input of the engine: the caller identifies
the session, optionally the conversation to continue, and the message text.
:class:`EngineResult` is the immutable record of one processed turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.conversation.context import ConversationContext
from backend.app.conversation.message import Message


class UserTurn(BaseModel):
    """A validated user turn submitted to the engine.

    Attributes:
        session_id: The session the turn belongs to.
        conversation_id: The conversation to continue; ``None`` starts a
            new conversation bound to the session.
        content: The user message text (non-empty).
    """

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    conversation_id: UUID | None = None
    content: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Immutable record of one processed user turn.

    Attributes:
        session_id: The session the turn was processed in.
        conversation_id: The conversation the messages were appended to.
        user_message: The appended user message.
        assistant_message: The appended assistant message.
        context: The context snapshot that was handed to the LLM port
            (contains the user message, never the assistant reply).
    """

    session_id: UUID
    conversation_id: UUID
    user_message: Message
    assistant_message: Message
    context: ConversationContext


__all__ = ["EngineResult", "UserTurn"]