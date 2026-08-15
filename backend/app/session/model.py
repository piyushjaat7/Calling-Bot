"""Session domain model — the lifecycle identity of an interaction.

A session represents one interaction between the platform and an external
caller (a phone call, a web chat, an API client). It is deliberately
*persistence-independent*: it holds no repository, database or framework
references and only knows how to manage its own lifecycle.

The lifecycle is minimal and strict:

* a session is born ``ACTIVE`` with its ``start_time`` set,
* :meth:`Session.end` moves it to ``ENDED`` and stamps ``end_time``,
* ending an already-ended session raises
  :class:`~backend.app.session.exceptions.SessionStateError`,
* ``ACTIVE`` sessions never carry an ``end_time`` and ``ENDED`` sessions
  always carry one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.session.exceptions import SessionStateError


def utc_now() -> datetime:
    """Return the current UTC time, timezone-aware.

    Returns:
        A timezone-aware ``datetime`` representing now in UTC.
    """
    return datetime.now(UTC)


class SessionStatus(StrEnum):
    """Lifecycle statuses of a session."""

    ACTIVE = "active"
    ENDED = "ended"


@dataclass(slots=True)
class Session:
    """A session identity with its lifecycle timestamps.

    The entity may only change through :meth:`end`; the constructor enforces
    the state/timestamp invariants so a malformed session can never enter
    the system.

    Attributes:
        session_id: Unique identifier of the session (UUID4).
        start_time: Session start timestamp (UTC, aware).
        end_time: Termination timestamp; ``None`` while ``ACTIVE``.
        status: Current lifecycle status.
    """

    session_id: UUID = field(default_factory=uuid4)
    start_time: datetime = field(default_factory=utc_now)
    end_time: datetime | None = None
    status: SessionStatus = field(default=SessionStatus.ACTIVE)

    def __post_init__(self) -> None:
        """Enforce the session lifecycle invariants after construction.

        Raises:
            ValueError: When the timestamps are naive, inconsistent with
                the status, or out of order.
        """
        if self.start_time.tzinfo is None:
            raise ValueError("Session start_time must be timezone-aware.")
        if self.end_time is not None and self.end_time.tzinfo is None:
            raise ValueError("Session end_time must be timezone-aware.")
        if self.status is SessionStatus.ACTIVE and self.end_time is not None:
            raise ValueError("An active session cannot have an end_time.")
        if self.status is SessionStatus.ENDED and self.end_time is None:
            raise ValueError("An ended session must have an end_time.")
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("Session end_time must not precede start_time.")

    @property
    def is_active(self) -> bool:
        """Whether the session is currently live."""
        return self.status is SessionStatus.ACTIVE

    @property
    def is_ended(self) -> bool:
        """Whether the session reached its terminal state."""
        return self.status is SessionStatus.ENDED

    def end(self) -> datetime:
        """End the session and stamp its termination time.

        Returns:
            The ``end_time`` set by this call.

        Raises:
            SessionStateError: When the session is already ended.
        """
        if self.status is SessionStatus.ENDED:
            raise SessionStateError(self.session_id)
        ended_at: datetime = utc_now()
        self.status = SessionStatus.ENDED
        self.end_time = ended_at
        return ended_at


__all__ = ["Session", "SessionStatus", "utc_now"]