"""Conversation Engine schemas.

:class:`UserTurn` is the validated input of the engine: the caller identifies
the session, optionally the conversation to continue, and the message text.
:class:`EngineResult` is the immutable record of one processed turn.
:class:`TurnResponse` and its helpers are the serializable HTTP envelope
built from an ``EngineResult`` by the REST layer.
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


class MessageView(BaseModel):
    """Serialized view of one conversation message.

    Attributes:
        message_id: The message identity.
        role: The message role (``user`` / ``assistant`` / ``system``).
        sequence: The per-conversation ordering index.
        content: The message text.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    message_id: UUID
    role: str
    sequence: int
    content: str


class TurnData(BaseModel):
    """Serialized data of one processed turn.

    Attributes:
        session_id: The session the turn was processed in.
        conversation_id: The conversation the messages were appended to.
        state: The conversation lifecycle state after the turn.
        turn_count: Number of user turns processed so far.
        user_message: The appended user message.
        assistant_message: The appended assistant message.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    session_id: UUID
    conversation_id: UUID
    state: str
    turn_count: int
    user_message: MessageView
    assistant_message: MessageView


class TurnResponse(BaseModel):
    """Success envelope returned by the conversation turn endpoint.

    Built directly from an :class:`EngineResult` via
    :meth:`TurnResponse.from_result`.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    message: str
    data: TurnData

    @classmethod
    def from_result(cls, result: EngineResult) -> TurnResponse:
        """Build the serialized response from a processed engine turn.

        Args:
            result: The engine result to serialize.

        Returns:
            The validated response envelope.
        """
        return cls(
            success=True,
            message="Turn processed.",
            data=TurnData(
                session_id=result.session_id,
                conversation_id=result.conversation_id,
                state=result.context.state.value,
                turn_count=result.context.turn_count,
                user_message=MessageView(
                    message_id=result.user_message.message_id,
                    role=result.user_message.role.value,
                    sequence=result.user_message.sequence,
                    content=result.user_message.content,
                ),
                assistant_message=MessageView(
                    message_id=result.assistant_message.message_id,
                    role=result.assistant_message.role.value,
                    sequence=result.assistant_message.sequence,
                    content=result.assistant_message.content,
                ),
            ),
        )


__all__ = [
    "EngineResult",
    "MessageView",
    "TurnData",
    "TurnResponse",
    "UserTurn",
]