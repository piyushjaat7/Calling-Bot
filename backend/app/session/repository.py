"""Session repository — the persistence boundary of the Session module.

:class:`SessionRepository` is an async ``Protocol``: the
:class:`~backend.app.session.service.SessionService` depends on it and
therefore never knows (or cares) whether sessions live in memory,
PostgreSQL, Redis or anywhere else. Only one implementation ships today —
:class:`SessionInMemoryRepository` — because the module is deliberately
persistence-free; future database adapters plug in behind the same
interface without touching the domain or the service.
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable
from uuid import UUID

from backend.app.session.model import Session


@runtime_checkable
class SessionRepository(Protocol):
    """Async persistence contract of the Session module.

    All operations are awaited; implementations own their concurrency and
    durability guarantees.
    """

    async def add(self, session: Session) -> None:
        """Store a new session.

        Args:
            session: The session to store.

        Raises:
            ValueError: When a session with the same identity exists.
        """

    async def get(self, session_id: UUID) -> Session | None:
        """Return the session with the given identity, or ``None``.

        Args:
            session_id: The session identifier to look up.

        Returns:
            The stored session, or ``None`` when unknown.
        """

    async def list(self) -> list[Session]:
        """Return every stored session in a deterministic order.

        Returns:
            All stored sessions, ordered by ``start_time`` then identity.
        """

    async def update(self, session: Session) -> None:
        """Persist the changes of an existing session.

        Args:
            session: The session to persist.

        Raises:
            KeyError: When no session with that identity is stored.
        """


class SessionInMemoryRepository:
    """An async-safe in-memory ``SessionRepository``.

    Backed by a plain dict guarded by an :class:`asyncio.Lock`, with
    deterministic ordering by ``start_time`` then ``session_id``. Intended
    for development, tests and single-process foundations only.
    """

    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def add(self, session: Session) -> None:
        """Store a new session (see :class:`SessionRepository`)."""
        async with self._lock:
            if session.session_id in self._sessions:
                raise ValueError(f"Session {session.session_id} already exists.")
            self._sessions[session.session_id] = session

    async def get(self, session_id: UUID) -> Session | None:
        """Return the stored session, or ``None`` (see :class:`SessionRepository`)."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def list(self) -> list[Session]:
        """Return every stored session in deterministic order."""
        async with self._lock:
            return sorted(
                self._sessions.values(),
                key=lambda session: (session.start_time, session.session_id),
            )

    async def update(self, session: Session) -> None:
        """Persist changes of an existing session (see :class:`SessionRepository`)."""
        async with self._lock:
            if session.session_id not in self._sessions:
                raise KeyError(session.session_id)
            self._sessions[session.session_id] = session


__all__ = ["SessionInMemoryRepository", "SessionRepository"]