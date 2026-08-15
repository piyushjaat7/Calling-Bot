"""Session application service.

Orchestrates the session use-cases (start, get, end) against the repository
abstraction. The service owns the flow — load, mutate through the domain
model, persist — and keeps the API layer thin. It never talks to a database
directly: persistence happens exclusively through
:class:`~backend.app.session.repository.SessionRepository`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.app.core.logger import LogContext, bind_context, get_logger
from backend.app.session.exceptions import (
    SessionNotFoundError,
    SessionStateError,
)
from backend.app.session.model import Session
from backend.app.session.repository import SessionRepository

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any


class SessionService:
    """Application service of the Session module.

    Attributes:
        repository: The persistence abstraction the service operates on.
    """

    def __init__(self, repository: SessionRepository) -> None:
        self.repository: SessionRepository = repository
        self._log: Logger = get_logger("session")

    async def start(self) -> Session:
        """Create and persist a new ``ACTIVE`` session.

        Returns:
            The started session.
        """
        session: Session = Session()
        await self.repository.add(session)
        self._log_session(session).info("Session started")
        return session

    async def get(self, session_id: UUID) -> Session:
        """Fetch a session by its identifier.

        Args:
            session_id: The session identifier to fetch.

        Returns:
            The stored session.

        Raises:
            SessionNotFoundError: When the session does not exist.
        """
        session: Session | None = await self.repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def end(self, session_id: UUID) -> Session:
        """End a session and persist the state change.

        Args:
            session_id: The session identifier to end.

        Returns:
            The ended session.

        Raises:
            SessionNotFoundError: When the session does not exist.
            SessionStateError: When the session is already ended.
        """
        session: Session = await self.get(session_id)
        try:
            session.end()
        except SessionStateError:
            self._log_session(session).warning("Session already ended")
            raise
        await self.repository.update(session)
        self._log_session(session).info("Session ended")
        return session

    def _log_session(self, session: Session) -> Logger:
        """Return the module logger bound with the session context."""
        return bind_context(self._log, LogContext(session_id=str(session.session_id)))


__all__ = ["SessionService"]