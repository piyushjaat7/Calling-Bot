"""Conversation domain events.

This module defines the *representation* of conversation events: the event
type vocabulary, the immutable :class:`ConversationEvent` record and helper
factories that build events from domain objects.

Events are deliberately decoupled from external delivery. Publishing is a
separate concern that belongs to the (future) ``ports.py`` layer — nothing
here emits or transports events.

Rules for payloads:
* Structured and sanitized — plain typed values only.
* Never include raw exceptions, tracebacks or internal objects.
* Correlation identifiers (``request_id``, ``caller_id``) travel on the
  event for the observability pipeline (matching the logging
  ``LogContext`` convention).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4

from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import Message, utc_now
from backend.app.conversation.state import StateTransition


class ConversationEventType(StrEnum):
    """Vocabulary of conversation-level domain events."""

    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_STARTED = "conversation.started"
    MESSAGE_APPENDED = "message.appended"
    STATE_CHANGED = "conversation.state_changed"
    TURN_COMPLETED = "conversation.turn_completed"
    CONVERSATION_ENDED = "conversation.ended"
    CONVERSATION_ERROR = "conversation.error"


@dataclass(frozen=True, slots=True)
class ConversationCorrelation:
    """Correlation identifiers carried by a conversation event.

    Attributes:
        request_id: Correlation id of the originating request.
        caller_id: Identifier of the external caller, when known.
    """

    request_id: str | None = None
    caller_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConversationEvent:
    """An immutable, structured conversation domain event.

    Attributes:
        event_id: Unique event identifier.
        conversation_id: The conversation that produced the event.
        session_id: The session the conversation belongs to.
        type: Event type from :class:`ConversationEventType`.
        occurred_at: Event timestamp (UTC).
        payload: Structured, sanitized event data (never exceptions).
        correlation: Correlation identifiers of the originating request.
    """

    conversation_id: UUID
    session_id: UUID
    type: ConversationEventType
    occurred_at: datetime = field(default_factory=utc_now)
    event_id: UUID = field(default_factory=uuid4)
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation: ConversationCorrelation = field(
        default_factory=ConversationCorrelation
    )

    def __post_init__(self) -> None:
        """Normalize the payload to an immutable mapping."""
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


# ---------------------------------------------------------------------------
# Event factories.
# ---------------------------------------------------------------------------


def created_event(
    conversation: Conversation, correlation: ConversationCorrelation | None = None
) -> ConversationEvent:
    """Build the ``conversation.created`` event.

    Args:
        conversation: The conversation that was created.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        type=ConversationEventType.CONVERSATION_CREATED,
        payload={"state": conversation.state.value},
        correlation=correlation or ConversationCorrelation(),
    )


def started_event(
    conversation: Conversation, correlation: ConversationCorrelation | None = None
) -> ConversationEvent:
    """Build the ``conversation.started`` event.

    Args:
        conversation: The conversation that entered ``ACTIVE``.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        type=ConversationEventType.CONVERSATION_STARTED,
        payload={"state": conversation.state.value},
        correlation=correlation or ConversationCorrelation(),
    )


def state_changed_event(
    conversation: Conversation,
    transition: StateTransition,
    correlation: ConversationCorrelation | None = None,
) -> ConversationEvent:
    """Build the ``conversation.state_changed`` event.

    Args:
        conversation: The conversation that changed state.
        transition: The recorded state transition.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        type=ConversationEventType.STATE_CHANGED,
        occurred_at=transition.occurred_at,
        payload={
            "from_state": transition.current.value,
            "to_state": transition.target.value,
        },
        correlation=correlation or ConversationCorrelation(),
    )


def message_appended_event(
    conversation: Conversation,
    message: Message,
    correlation: ConversationCorrelation | None = None,
) -> ConversationEvent:
    """Build the ``message.appended`` event.

    Args:
        conversation: The conversation the message was appended to.
        message: The appended message.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        type=ConversationEventType.MESSAGE_APPENDED,
        occurred_at=message.created_at,
        payload={
            "message_id": str(message.message_id),
            "role": message.role.value,
            "sequence": message.sequence,
            # Content is plain text and intentionally included; it is not
            # sensitive metadata.
            "message": message.content,
        },
        correlation=correlation or ConversationCorrelation(),
    )


def ended_event(
    conversation: Conversation, correlation: ConversationCorrelation | None = None
) -> ConversationEvent:
    """Build the ``conversation.ended`` event.

    Args:
        conversation: The conversation that ended.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation.conversation_id,
        session_id=conversation.session_id,
        type=ConversationEventType.CONVERSATION_ENDED,
        payload={
            "state": conversation.state.value,
            "ended_at": (
                conversation.ended_at.isoformat() if conversation.ended_at else None
            ),
        },
        correlation=correlation or ConversationCorrelation(),
    )


def error_event(
    conversation_id: UUID,
    session_id: UUID,
    message: str,
    correlation: ConversationCorrelation | None = None,
) -> ConversationEvent:
    """Build a sanitized ``conversation.error`` event.

    The payload carries only the plain error message; raw exceptions or
    tracebacks are never included.

    Args:
        conversation_id: The affected conversation.
        session_id: The session the conversation belongs to.
        message: A sanitized, human readable error description.
        correlation: Optional correlation identifiers.

    Returns:
        The structured event.
    """
    return ConversationEvent(
        conversation_id=conversation_id,
        session_id=session_id,
        type=ConversationEventType.CONVERSATION_ERROR,
        payload={"error": message},
        correlation=correlation or ConversationCorrelation(),
    )


__all__ = [
    "ConversationCorrelation",
    "ConversationEvent",
    "ConversationEventType",
    "created_event",
    "ended_event",
    "error_event",
    "message_appended_event",
    "started_event",
    "state_changed_event",
]