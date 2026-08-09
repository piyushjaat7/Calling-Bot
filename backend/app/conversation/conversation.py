"""Conversation domain entity of the Conversation Core.

A conversation is the dialogue-level identity of an interaction. It owns
its messages, its lifecycle state (driven exclusively by the
:class:`~backend.app.conversation.state.ConversationStateMachine`) and its
metadata.

Conversation is intentionally *independent* from the Session system: it
only stores the ``session_id`` it belongs to as an opaque identifier and
does not enforce any permanent 1:1 relationship — the association is the
concern of whoever creates the conversation. No session implementation is
ever imported here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from uuid import UUID, uuid4

from backend.app.conversation.message import Message, MessageRole, utc_now
from backend.app.conversation.state import (
    STATE_MACHINE,
    ConversationState,
    StateTransition,
)


class ConversationClosedError(ValueError):
    """Raised when an operation requires a live conversation."""

    def __init__(self, conversation_id: UUID) -> None:
        super().__init__(f"Conversation {conversation_id} is already ended.")
        self.conversation_id: UUID = conversation_id


@dataclass(slots=True)
class Conversation:
    """A single dialogue, owned by the Conversation Core.

    The entity may mutate, but only through its explicit domain methods
    (:meth:`add_message`, :meth:`start`, :meth:`end`); the field values
    themselves are never exposed for direct mutation.

    Attributes:
        conversation_id: Unique identity of the conversation.
        session_id: Opaque reference to the owning session; the association
            is *not* enforced as a permanent 1:1 by this model.
        metadata: Structured, plain-text context keyed by name (e.g.
            ``channel``, ``request_id``)
        state: Current lifecycle state (driven by the state machine).
        created_at / updated_at / ended_at: life timestamps (UTC).
    """

    session_id: UUID
    conversation_id: UUID = field(default_factory=uuid4)
    metadata: Mapping[str, str] = field(default_factory=dict)
    _state: ConversationState = field(
        default=ConversationState.CREATED, init=False, repr=False
    )
    _messages: list[Message] = field(default_factory=list, init=False, repr=False)
    _transitions: list[StateTransition] = field(
        default_factory=list, init=False, repr=False
    )
    _created_at: datetime = field(default_factory=utc_now, init=False)
    _updated_at: datetime = field(default_factory=utc_now, init=False)
    _ended_at: datetime | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize the metadata to an immutable mapping."""
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    # -- Read-only views ----------------------------------------------------

    @property
    def state(self) -> ConversationState:
        """The current lifecycle state."""
        return self._state

    @property
    def created_at(self) -> datetime:
        """Conversation creation timestamp (UTC)."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Timestamp of the last mutation (UTC)."""
        return self._updated_at

    @property
    def ended_at(self) -> datetime | None:
        """Termination timestamp, or ``None`` while the conversation is live."""
        return self._ended_at

    @property
    def messages(self) -> tuple[Message, ...]:
        """Immutable view of every message in sequence order."""
        return tuple(self._messages)

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        """Every state transition performed so far, in order."""
        return tuple(self._transitions)

    @property
    def is_ended(self) -> bool:
        """Whether the conversation has reached its terminal state."""
        return self._state is ConversationState.ENDED

    # -- Domain operations ---------------------------------------------------

    def start(self) -> StateTransition:
        """Open the conversation for dialogue (``CREATED`` -> ``ACTIVE``).

        Returns:
            The performed transition.

        Raises:
            InvalidStateTransitionError: When the conversation is not in
                ``CREATED`` state.
        """
        return self._record(
            STATE_MACHINE.transition(self._state, ConversationState.ACTIVE)
        )

    def end(self) -> StateTransition:
        """End the conversation (``ACTIVE``/``CREATED`` -> ``ENDED``).

        Returns:
            The performed transition.

        Raises:
            ConversationClosedError: When the conversation is already ended.
            InvalidStateTransitionError: When the current state cannot end.
        """
        if self._state is ConversationState.ENDED:
            raise ConversationClosedError(self.conversation_id)
        transition: StateTransition = STATE_MACHINE.transition(
            self._state, ConversationState.ENDED
        )
        object.__setattr__(self, "_ended_at", transition.occurred_at)
        return self._record(transition)

    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Mapping[str, str] | None = None,
    ) -> Message:
        """Append a message and lock in its sequence number.

        The first message of a conversation advances the state from
        ``CREATED`` to ``ACTIVE``. A conversation that is already ``ENDED``
        rejects the operation.

        Args:
            role: Role of the message author.
            content: The message body (non-empty, capped length).
            metadata: Optional structured context for the message.

        Returns:
            The immutable message that was appended.

        Raises:
            ConversationClosedError: When the conversation is ended.
            ValueError: When the content is empty or too long.
        """
        if self._state is ConversationState.ENDED:
            raise ConversationClosedError(self.conversation_id)

        message: Message = Message(
            conversation_id=self.conversation_id,
            sequence=len(self._messages),
            role=role,
            content=content,
            metadata=metadata or {},
        )
        object.__setattr__(self, "_updated_at", message.created_at)
        self._messages.append(message)

        if self._state is ConversationState.CREATED:
            self._record(
                STATE_MACHINE.transition(
                    self._state, ConversationState.ACTIVE, occurred_at=message.created_at
                )
            )
        return message

    def _record(self, transition: StateTransition) -> StateTransition:
        """Apply and record a validated transition."""
        object.__setattr__(self, "_state", transition.target)
        object.__setattr__(self, "_updated_at", transition.occurred_at)
        self._transitions.append(transition)
        return transition


__all__ = [
    "Conversation",
    "ConversationClosedError",
]