"""Conversation context — the LLM-independent snapshot of a conversation.

The context is the read-only, serialized view that downstream consumers
(the future AI layer) receive. It deliberately contains:

* no prompts, instructions or system text,
* no provider or model names,
* no provider-specific fields.

It is assembled from pure domain objects by :func:`build_context` and
carries only structured, typed information. The reserved extension slots
(``memory_excerpts``, ``tool_results``) are plain-text tuples kept empty
until the memory/tool systems exist; their shape may evolve behind this
module without breaking consumers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import Message, MessageRole
from backend.app.conversation.state import ConversationState

#: How many most-recent messages the context exposes.
RECENT_MESSAGE_WINDOW: int = 20


@dataclass(frozen=True, slots=True)
class SessionView:
    """Minimal, interface-independent view of a session.

    Deliberately a *view*: a plain data snapshot, never a live session
    object. The Session system (a separate module) provides these; the
    Conversation Core only reads them.

    Attributes:
        session_id: The session identity.
        caller_id: The external caller id, when known.
        status: Session lifecycle status string (owned by the Session
            system's vocabulary).
        channel: Interface the session came through (e.g. ``phone``).
        started_at: Session start time, when known.
        metadata: Structured session context (plain values only).
    """

    session_id: UUID
    caller_id: str | None = None
    status: str = "unknown"
    channel: str | None = None
    started_at: datetime | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize the metadata to an immutable mapping."""
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Immutable snapshot of one conversation for downstream consumers.

    Attributes:
        conversation_id: The conversation identity.
        session_id: The session the conversation belongs to.
        state: Current conversation state.
        messages: The most recent messages in sequence order (windowed).
        turn_count: Number of user turns processed so far.
        session: Optional session snapshot (``None`` when unknown).
        memory_excerpts: Reserved — plain-text memory excerpts (empty).
        tool_results: Reserved — plain-text tool result summaries (empty).
    """

    conversation_id: UUID
    session_id: UUID
    state: ConversationState
    messages: tuple[Message, ...]
    turn_count: int
    session: SessionView | None = None
    memory_excerpts: tuple[str, ...] = ()
    tool_results: tuple[str, ...] = ()


def build_context(
    conversation: Conversation,
    session: SessionView | None = None,
    memory_excerpts: tuple[str, ...] = (),
    tool_results: tuple[str, ...] = (),
) -> ConversationContext:
    """Assemble the current conversation context snapshot.

    Args:
        conversation: The live conversation to snapshot.
        session: Optional session view to attach.
        memory_excerpts: Reserved plain-text memory excerpts.
        tool_results: Reserved plain-text tool result summaries.

    Returns:
        An immutable, LLM-independent context snapshot.
    """
    recent: tuple[Message, ...] = conversation.messages[-RECENT_MESSAGE_WINDOW:]
    turn_count: int = sum(
        1 for message in conversation.messages if message.role is MessageRole.USER
    )
    return ConversationContext(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        state=conversation.state,
        messages=recent,
        turn_count=turn_count,
        session=session,
        memory_excerpts=memory_excerpts,
        tool_results=tool_results,
    )


__all__ = [
    "RECENT_MESSAGE_WINDOW",
    "ConversationContext",
    "SessionView",
    "build_context",
]