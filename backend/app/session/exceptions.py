"""Session domain exceptions.

Every error raised by the Session domain, service or repository derives from
:class:`SessionError`, so callers can catch the whole hierarchy with a single
``except SessionError`` while the domain stays free of framework or
persistence concerns.
"""

from __future__ import annotations

from uuid import UUID


class SessionError(Exception):
    """Base class of every Session domain error."""


class SessionNotFoundError(SessionError):
    """Raised when the requested session does not exist.

    Attributes:
        session_id: The identifier that was looked up.
    """

    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found.")
        self.session_id: UUID = session_id


class SessionStateError(SessionError):
    """Raised when an operation conflicts with the session lifecycle state.

    Currently the only conflicting operation is ending a session that is
    already ``ENDED``; the class stays general so future state violations
    (e.g. restarting a terminated session) share the same error contract.

    Attributes:
        session_id: The identifier of the session in an invalid state.
    """

    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} is already ended.")
        self.session_id: UUID = session_id


__all__ = ["SessionError", "SessionNotFoundError", "SessionStateError"]