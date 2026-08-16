"""Tests of the PostgreSQL-backed session repository (isolated on SQLite).

The same repository implementation runs against PostgreSQL in production;
here it is exercised against an in-memory SQLite database that mirrors the
production schema (see ``tests/conftest.py``).
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from backend.app.session.model import Session, utc_now
from backend.app.session.repository import (
    SessionPostgresRepository,
    SessionRepository,
)


@pytest.fixture
def repo(
    sqlite_session_factory: object,
) -> SessionPostgresRepository:
    """A PostgreSQL-backed repository bound to the isolated SQLite engine."""
    return SessionPostgresRepository(sqlite_session_factory)


class TestPostgresRepository:
    async def test_empty_list(self, repo: SessionPostgresRepository) -> None:
        assert await repo.list() == []

    async def test_add_and_get_roundtrip(
        self, repo: SessionPostgresRepository
    ) -> None:
        session = Session()
        await repo.add(session)
        stored = await repo.get(session.session_id)
        assert stored is not None
        assert stored.session_id == session.session_id
        assert stored.start_time == session.start_time
        assert stored.end_time is None
        assert stored.status is session.status

    async def test_get_missing_returns_none(
        self, repo: SessionPostgresRepository
    ) -> None:
        assert await repo.get(uuid4()) is None

    async def test_add_duplicate_raises(
        self, repo: SessionPostgresRepository
    ) -> None:
        session = Session()
        await repo.add(session)
        with pytest.raises(ValueError, match="already exists"):
            await repo.add(session)

    async def test_list_returns_all_sessions(
        self, repo: SessionPostgresRepository
    ) -> None:
        sessions = [Session() for _ in range(3)]
        for session in sessions:
            await repo.add(session)
        stored = await repo.list()
        assert [s.session_id for s in stored] == [s.session_id for s in sessions]

    async def test_list_deterministic_order(
        self, repo: SessionPostgresRepository
    ) -> None:
        sessions = [
            Session(start_time=utc_now() + timedelta(seconds=index))
            for index in range(3)
        ]
        for session in sessions:
            await repo.add(session)
        stored = await repo.list()
        assert [s.session_id for s in stored] == [s.session_id for s in sessions]

    async def test_update_persists_changes(
        self, repo: SessionPostgresRepository
    ) -> None:
        session = Session()
        await repo.add(session)
        session.end()
        await repo.update(session)
        stored = await repo.get(session.session_id)
        assert stored is not None
        assert stored.status is session.status
        assert stored.end_time == session.end_time

    async def test_update_missing_raises(
        self, repo: SessionPostgresRepository
    ) -> None:
        with pytest.raises(KeyError):
            await repo.update(Session())

    async def test_persistence_across_repositories(
        self, sqlite_session_factory: object
    ) -> None:
        first = SessionPostgresRepository(sqlite_session_factory)
        second = SessionPostgresRepository(sqlite_session_factory)
        session = Session()
        await first.add(session)
        stored = await second.get(session.session_id)
        assert stored is not None
        assert stored.session_id == session.session_id

    async def test_datetimes_are_aware_utc(
        self, repo: SessionPostgresRepository
    ) -> None:
        session = Session()
        await repo.add(session)
        stored = await repo.get(session.session_id)
        assert stored is not None
        for value in (stored.start_time,):
            assert value.tzinfo is not None
            assert value.utcoffset() == timedelta(0)

    def test_implements_protocol(self) -> None:
        assert isinstance(SessionPostgresRepository(object), SessionRepository)