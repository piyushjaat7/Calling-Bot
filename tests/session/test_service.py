"""Tests of the SessionService against the repository abstraction."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from backend.app.session.exceptions import (
    SessionNotFoundError,
    SessionStateError,
)
from backend.app.session.model import Session, SessionStatus
from backend.app.session.repository import (
    SessionInMemoryRepository,
    SessionRepository,
)
from backend.app.session.service import SessionService


class RecordingRepository:
    """Minimal session repository used to prove the service abstraction."""

    def __init__(self) -> None:
        self.sessions: dict[UUID, Session] = {}
        self.added: list[Session] = []

    async def add(self, session: Session) -> None:
        self.sessions[session.session_id] = session
        self.added.append(session)

    async def get(self, session_id: UUID) -> Session | None:
        return self.sessions.get(session_id)

    async def list(self) -> list[Session]:
        return list(self.sessions.values())

    async def update(self, session: Session) -> None:
        self.sessions[session.session_id] = session


class TestSessionService:
    async def test_start_persists_active_session(
        self,
        session_service: SessionService,
        session_repository: SessionInMemoryRepository,
    ) -> None:
        session = await session_service.start()
        assert session.status is SessionStatus.ACTIVE
        assert session.end_time is None
        stored = await session_repository.get(session.session_id)
        assert stored is session

    async def test_start_generates_unique_ids(self, session_service: SessionService) -> None:
        first = await session_service.start()
        second = await session_service.start()
        assert isinstance(first.session_id, UUID)
        assert first.session_id != second.session_id

    async def test_get_returns_started_session(self, session_service: SessionService) -> None:
        session = await session_service.start()
        fetched = await session_service.get(session.session_id)
        assert fetched is session

    async def test_get_missing_raises_not_found(self, session_service: SessionService) -> None:
        with pytest.raises(SessionNotFoundError):
            await session_service.get(uuid4())

    async def test_end_persists_ended_session(
        self,
        session_service: SessionService,
        session_repository: SessionInMemoryRepository,
    ) -> None:
        session = await session_service.start()
        ended = await session_service.end(session.session_id)
        assert ended is session
        assert session.status is SessionStatus.ENDED
        assert session.end_time is not None
        stored = await session_repository.get(session.session_id)
        assert stored is not None
        assert stored.status is SessionStatus.ENDED

    async def test_end_missing_raises_not_found(self, session_service: SessionService) -> None:
        with pytest.raises(SessionNotFoundError):
            await session_service.end(uuid4())

    async def test_end_twice_raises_state_error(
        self, session_service: SessionService
    ) -> None:
        session = await session_service.start()
        await session_service.end(session.session_id)
        with pytest.raises(SessionStateError) as excinfo:
            await session_service.end(session.session_id)
        assert excinfo.value.session_id == session.session_id


class TestServiceAgainstStub:
    def test_stub_conforms_to_protocol(self) -> None:
        assert isinstance(RecordingRepository(), SessionRepository)

    async def test_service_uses_the_repository_abstraction(self) -> None:
        repository = RecordingRepository()
        service = SessionService(repository)
        session = await service.start()
        ended = await service.end(session.session_id)
        assert ended.status is SessionStatus.ENDED
        assert len(repository.added) == 1
        assert repository.sessions[session.session_id].status is SessionStatus.ENDED