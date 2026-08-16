"""Session repository — the persistence boundary of the Session module.

:class:`SessionRepository` is an async ``Protocol``: the
:class:`~backend.app.session.service.SessionService` depends on it and
therefore never knows (or cares) whether sessions live in memory,
PostgreSQL, Redis or anywhere else. Two implementations ship today:

* :class:`SessionInMemoryRepository` — the development/test in-memory
  adapter,
* :class:`SessionPostgresRepository` — the production adapter backed by
  PostgreSQL (SQLAlchemy async).

Future database adapters plug in behind the same interface without touching
the domain or the service.
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.database.models import SessionRecord
from backend.app.session.model import Session, SessionStatus


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


class SessionPostgresRepository:
    """Async ``SessionRepository`` backed by PostgreSQL (SQLAlchemy).

    Args:
        session_factory: An ``async_sessionmaker`` bound to the database
            engine.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, session: Session) -> None:
        """Store a new session (see :class:`SessionRepository`).

        Raises:
            ValueError: When a session with the same identity exists.
        """
        async with self._session_factory() as db, db.begin():
            if await db.get(SessionRecord, session.session_id) is not None:
                raise ValueError(f"Session {session.session_id} already exists.")
            db.add(self._to_record(session))

    async def get(self, session_id: UUID) -> Session | None:
        """Return the stored session, or ``None`` (see :class:`SessionRepository`)."""
        async with self._session_factory() as db:
            row: SessionRecord | None = await db.get(SessionRecord, session_id)
        return self._to_domain(row) if row is not None else None

    async def list(self) -> list[Session]:
        """Return every stored session in deterministic order."""
        async with self._session_factory() as db:
            rows = (
                (
                    await db.execute(
                        select(SessionRecord).order_by(
                            SessionRecord.start_time, SessionRecord.session_id
                        )
                    )
                )
                .scalars()
                .all()
            )
        return [self._to_domain(row) for row in rows]

    async def update(self, session: Session) -> None:
        """Persist changes of an existing session (see :class:`SessionRepository`).

        Raises:
            KeyError: When no session with that identity is stored.
        """
        async with self._session_factory() as db, db.begin():
            row: SessionRecord | None = await db.get(
                SessionRecord, session.session_id
            )
            if row is None:
                raise KeyError(session.session_id)
            row.start_time = session.start_time
            row.end_time = session.end_time
            row.status = session.status.value

    @staticmethod
    def _to_record(session: Session) -> SessionRecord:
        """Map the domain session onto its storage record."""
        return SessionRecord(
            session_id=session.session_id,
            start_time=session.start_time,
            end_time=session.end_time,
            status=session.status.value,
        )

    @staticmethod
    def _to_domain(row: SessionRecord) -> Session:
        """Rebuild the domain session from its storage record."""
        return Session(
            session_id=row.session_id,
            start_time=row.start_time,
            end_time=row.end_time,
            status=SessionStatus(row.status),
        )


__all__ = ["SessionInMemoryRepository", "SessionPostgresRepository", "SessionRepository"]