"""Message domain model of the Conversation Core.

A message is an immutable value object: once created it can never change.
Messages are the atomic units of a conversation and are ordered strictly by
their ``sequence`` number (never by timestamps), enforced by
:class:`~backend.app.conversation.conversation.Conversation`.

The ``TOOL_RESULT`` role is reserved for the future tool-execution sprint so
the domain model never needs a breaking schema change; nothing in this
package consumes it yet.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Final
from uuid import UUID, uuid4

#: Upper bound of a single message content in characters.
MAX_MESSAGE_CHARS: Final[int] = 4096


def utc_now() -> datetime:
    """Return the current UTC time, timezone-aware.

    Returns:
        A timezone-aware ``datetime`` representing now in UTC.
    """
    return datetime.now(UTC)


class MessageRole(StrEnum):
    """Semantic role of a message inside a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    #: Reserved for the future tool-execution sprint.
    TOOL_RESULT = "tool_result"


@dataclass(frozen=True, slots=True)
class Message:
    """An immutable conversational message.

    A message is fully immutable after creation: identity, conversation
    binding, ordering, content and timestamps can never change. Ordering is
    defined by ``sequence``, a per-conversation monotonic counter that is
    assigned by the owning :class:`Conversation` and is unique within it.

    Attributes:
        conversation_id: The conversation this message belongs to.
        sequence: Monotonic per-conversation ordering index (0-based).
        role: Semantic role of the message.
        content: The message text (non-empty, length capped).
        created_at: Time the message was created (UTC, aware).
        message_id: Unique identifier of the message.
        metadata: Immutable structured context attached to the message
            (e.g. ``source``, ``request_id``); plain text values only.
    """

    conversation_id: UUID
    sequence: int
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=utc_now)
    message_id: UUID = field(default_factory=uuid4)
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Enforce the message invariants after construction."""
        if not isinstance(self.content, str):
            raise TypeError("Message content must be a string.")
        if self.sequence < 0:
            raise ValueError("Message sequence must be a non-negative integer.")
        if not self.content.strip():
            raise ValueError("Message content must not be empty.")
        if len(self.content) > MAX_MESSAGE_CHARS:
            raise ValueError(
                f"Message content exceeds the limit of {MAX_MESSAGE_CHARS} characters."
            )
        object.__setattr__(
            self, "metadata", MappingProxyType(dict(self.metadata))
        )


__all__ = [
    "MAX_MESSAGE_CHARS",
    "Message",
    "MessageRole",
    "utc_now",
]