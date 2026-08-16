"""SessionPort adapter — bridges the Session service to the Conversation Engine.

The Conversation Core only knows the ``SessionPort`` protocol from
:mod:`backend.app.conversation.ports` and the read-only
:class:`~backend.app.conversation.context.SessionView`; it never imports the
Session module. This adapter is the bridge the Session system provides: it
wraps a :class:`~backend.app.session.service.SessionService` and translates
its domain result (or ``SessionNotFoundError``) into the view contract the
engine expects.
"""

from __future__ import annotations

from uuid import UUID

from backend.app.conversation.context import SessionView
from backend.app.session.exceptions import SessionNotFoundError
from backend.app.session.model import Session
from backend.app.session.service import SessionService


class ServiceSessionPort:
    """``SessionPort`` implementation backed by a ``SessionService``.

    Args:
        service: The session application service to delegate lookups to.
    """

    def __init__(self, service: SessionService) -> None:
        self._service: SessionService = service

    async def get(self, session_id: UUID) -> SessionView | None:
        """Return the session view, or ``None`` when the session is unknown.

        Args:
            session_id: The session identifier to look up.

        Returns:
            A read-only session view when the session exists, ``None``
            otherwise.
        """
        try:
            session: Session = await self._service.get(session_id)
        except SessionNotFoundError:
            return None
        return SessionView(
            session_id=session.session_id,
            status=session.status.value,
            started_at=session.start_time,
        )


__all__ = ["ServiceSessionPort"]