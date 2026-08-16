"""Tests of the in-memory session repository."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from backend.app.session.model import Session, utc_now
from backend.app.session.repository import (
    SessionInMemoryRepository,
    SessionRepository,
)


class TestInMemoryRepository:
    async def test_empty_list(self, session_repository: SessionInMemoryRepository) -> None:
        assert await session_repository.list() == []

    async def test_add_and_get_roundtrip(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        session = Session()
        await session_repository.add(session)
        stored = await session_repository.get(session.session_id)
        assert stored is session

    async def test_get_missing_returns_none(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        assert await session_repository.get(uuid4()) is None

    async def test_add_duplicate_raises(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        session = Session()
        await session_repository.add(session)
        with pytest.raises(ValueError, match="already exists"):
            await session_repository.add(session)

    async def test_list_returns_all_sessions(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        sessions = [Session() for _ in range(3)]
        for session in sessions:
            await session_repository.add(session)
        stored = await session_repository.list()
        assert [s.session_id for s in stored] == [s.session_id for s in sessions]

    async def test_list_deterministic_order(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        sessions = [
            Session(start_time=utc_now() + timedelta(seconds=index))
            for index in range(3)
        ]
        for session in sessions:
            await session_repository.add(session)
        stored = await session_repository.list()
        assert [s.session_id for s in stored] == [s.session_id for s in sessions]

    async def test_update_persists_changes(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        session = Session()
        await session_repository.add(session)
        session.end()
        await session_repository.update(session)
        stored = await session_repository.get(session.session_id)
        assert stored is not None
        assert stored.status is session.status
        assert stored.end_time == session.end_time

    async def test_update_missing_raises(
        self, session_repository: SessionInMemoryRepository
    ) -> None:
        with pytest.raises(KeyError):
            await session_repository.update(Session())

    def test_implements_protocol(self) -> None:
        assert isinstance(SessionInMemoryRepository(), SessionRepository)