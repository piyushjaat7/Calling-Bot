"""Conversation state machine — table-driven, fully testable.

The conversation lifecycle is modelled as a finite state machine whose
transition rules live in a single explicit table (:data:`_TRANSITIONS`).
The machine itself is stateless: it validates and performs transitions
against a caller-provided current state and records every applied
transition as an immutable :class:`StateTransition`.

Rules enforced here:

* ``ENDED`` is terminal — no transition may leave it.
* Every transition must be declared in the table; anything else raises
  :class:`InvalidStateTransitionError`.
* ``SUSPENDED`` is a reserved state (future external-input waits, e.g.
  tool execution); no transition involves it until a consumer needs it.

The machine never makes decisions about *why* a transition happens — that
is the caller's (Conversation/Engine) responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from backend.app.conversation.message import utc_now


class ConversationState(StrEnum):
    """Lifecycle states of a conversation."""

    CREATED = "created"
    ACTIVE = "active"
    #: Reserved for future waits on external input (never transitioned yet).
    SUSPENDED = "suspended"
    ENDED = "ended"


class InvalidStateTransitionError(ValueError):
    """Raised when a transition is not allowed by the transition table."""

    def __init__(
        self,
        current: ConversationState,
        target: ConversationState,
    ) -> None:
        super().__init__(
            f"Invalid conversation state transition: {current.value} -> "
            f"{target.value}."
        )
        self.current: ConversationState = current
        self.target: ConversationState = target


#: The single source of truth for allowed transitions.
_TRANSITIONS: Final[dict[ConversationState, frozenset[ConversationState]]] = {
    ConversationState.CREATED: frozenset(
        {ConversationState.ACTIVE, ConversationState.ENDED}
    ),
    ConversationState.ACTIVE: frozenset(
        {ConversationState.ACTIVE, ConversationState.ENDED}
    ),
    #: Reserved; no valid transitions touch SUSPENDED yet.
    ConversationState.SUSPENDED: frozenset(),
    #: Terminal: nothing may leave ENDED.
    ConversationState.ENDED: frozenset(),
}

#: Conversation states from which no transition is allowed.
_TERMINAL_STATES: Final[frozenset[ConversationState]] = frozenset(
    {ConversationState.ENDED}
)


@dataclass(frozen=True, slots=True)
class StateTransition:
    """An immutable record of one performed transition.

    Attributes:
        current: The state before the transition.
        target: The state after the transition.
        occurred_at: Time the transition was performed (UTC).
    """

    current: ConversationState
    target: ConversationState
    occurred_at: datetime


class ConversationStateMachine:
    """Stateless validator and executor of conversation transitions."""

    _TRANSITIONS_TABLE = _TRANSITIONS
    _TERMINAL = _TERMINAL_STATES

    def valid_targets(self, state: ConversationState) -> frozenset[ConversationState]:
        """Return every target state reachable from ``state``.

        Args:
            state: The current state.

        Returns:
            The set of directly reachable states.
        """
        return self._TRANSITIONS_TABLE[state]

    def can_transition(
        self, current: ConversationState, target: ConversationState
    ) -> bool:
        """Tell whether a transition is allowed by the table.

        Args:
            current: The state before the transition.
            target: The desired state after the transition.

        Returns:
            ``True`` when the transition is declared, ``False`` otherwise.
        """
        return target in self._TRANSITIONS_TABLE[current]

    def is_terminal(self, state: ConversationState) -> bool:
        """Return whether ``state`` is a terminal state.

        Args:
            state: The state to inspect.

        Returns:
            ``True`` when the state is terminal.
        """
        return state in self._TERMINAL

    def transition(
        self,
        current: ConversationState,
        target: ConversationState,
        occurred_at: datetime | None = None,
    ) -> StateTransition:
        """Perform a transition, raising on any table violation.

        Args:
            current: The state before the transition.
            target: The desired state after the transition.
            occurred_at: Optional transition timestamp (UTC); defaults to
                the current UTC time.

        Returns:
            The immutable record of the performed transition.

        Raises:
            InvalidStateTransitionError: When the transition is not declared
                in the transition table.
        """
        if not self.can_transition(current, target):
            raise InvalidStateTransitionError(current, target)
        return StateTransition(
            current=current,
            target=target,
            occurred_at=occurred_at if occurred_at is not None else utc_now(),
        )


#: Process-wide shared instance (the machine holds no state).
STATE_MACHINE: Final[ConversationStateMachine] = ConversationStateMachine()

__all__ = [
    "STATE_MACHINE",
    "ConversationState",
    "ConversationStateMachine",
    "InvalidStateTransitionError",
    "StateTransition",
]