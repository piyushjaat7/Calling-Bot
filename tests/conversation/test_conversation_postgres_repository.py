"""Tests of the PostgreSQL-backed conversation repository (isolated on SQLite).

The repository runs against PostgreSQL in production; here it is exercised
against an in-memory SQLite database mirroring the production schema (see
``tests/conftest.py``), including engine-driven persistence flows.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.conversation.context import SessionView
from backend.app.conversation.conversation import Conversation
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.message import MessageRole
from backend.app.conversation.ports import ConversationRepository
from backend.app.conversation.repository import ConversationPostgresRepository
from backend.app.conversation.schemas import UserTurn
from backend.app.database import ConversationRecord
from backend.app.session.model import Session
from backend.app.session.repository import SessionPostgresRepository
from tests.conversation.fakes import FakeLlmPort, FakeSessionPort


@pytest.fixture
def repo(sqlite_session_factory: object) -> ConversationPostgresRepository:
    """A PostgreSQL-backed repository bound to the isolated SQLite engine."""
    return ConversationPostgresRepository(sqlite_session_factory)


@pytest.fixture
async def session_id(
    sqlite_session_factory: object,
) -> UUID:
    """A persisted session for the conversation FK constraint."""
    session = Session()
    await SessionPostgresRepository(sqlite_session_factory).add(session)
    return session.session_id


class TestPostgresRepository:
    async def test_save_and_get_roundtrip(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id, metadata={"channel": "voice"})
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert stored.conversation_id == conversation.conversation_id
        assert stored.session_id == session_id
        assert stored.state is conversation.state
        assert stored.metadata == {"channel": "voice"}
        assert stored.created_at == conversation.created_at
        assert stored.updated_at == conversation.updated_at
        assert stored.ended_at is None
        assert stored.messages == ()
        assert not stored.is_ended

    async def test_get_missing_returns_none(
        self, repo: ConversationPostgresRepository
    ) -> None:
        assert await repo.get(uuid4()) is None

    async def test_save_persists_messages_in_sequence_order(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        first = conversation.add_message(MessageRole.USER, "Hello")
        second = conversation.add_message(MessageRole.ASSISTANT, "Hi there")
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert [m.message_id for m in stored.messages] == [
            first.message_id,
            second.message_id,
        ]
        assert [m.content for m in stored.messages] == ["Hello", "Hi there"]
        assert [m.role for m in stored.messages] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]
        assert [m.sequence for m in stored.messages] == [0, 1]
        assert stored.state.name == "ACTIVE"

    async def test_save_is_idempotent(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        conversation.add_message(MessageRole.USER, "Hello")
        conversation.add_message(MessageRole.ASSISTANT, "Hi there")
        await repo.save(conversation)
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert len(stored.messages) == 2

    async def test_save_after_append_updates_rows(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        await repo.save(conversation)
        conversation.add_message(MessageRole.USER, "Hello")
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert len(stored.messages) == 1
        assert stored.updated_at >= stored.created_at

    async def test_end_persists_state_and_ended_at(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        await repo.save(conversation)
        conversation.end()
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert stored.is_ended
        assert stored.state.name == "ENDED"
        assert stored.ended_at is not None

    async def test_hydrated_conversation_stays_usable(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        stored.add_message(MessageRole.USER, "Hello")
        await repo.save(stored)
        again = await repo.get(conversation.conversation_id)
        assert again is not None
        assert [m.content for m in again.messages] == ["Hello"]

    async def test_message_metadata_roundtrip(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        message = conversation.add_message(
            MessageRole.USER, "Hello", metadata={"source": "voice"}
        )
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        assert stored.messages[0].metadata == {"source": "voice"}
        assert message.metadata == {"source": "voice"}

    async def test_unknown_session_rolls_back(
        self, repo: ConversationPostgresRepository
    ) -> None:
        conversation = Conversation(session_id=uuid4())
        with pytest.raises(IntegrityError):
            await repo.save(conversation)
        assert await repo.get(conversation.conversation_id) is None

    async def test_datetimes_are_aware_utc(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        conversation = Conversation(session_id=session_id)
        await repo.save(conversation)
        stored = await repo.get(conversation.conversation_id)
        assert stored is not None
        for value in (stored.created_at, stored.updated_at):
            assert value.tzinfo is not None
            assert value.utcoffset() == timedelta(0)

    def test_implements_protocol(self) -> None:
        assert isinstance(ConversationPostgresRepository(object), ConversationRepository)


class TestEngineWithStore:
    async def test_turn_persists_conversation(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        engine = ConversationEngine(
            llm=FakeLlmPort(),
            sessions=FakeSessionPort({session_id: SessionView(session_id=session_id)}),
            repository=repo,
        )
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        stored = await repo.get(result.conversation_id)
        assert stored is not None
        assert [m.content for m in stored.messages] == ["Hello", "Hello there."]
        assert [m.role for m in stored.messages] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]

    async def test_new_engine_resolves_persisted_conversation(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        first = ConversationEngine(
            llm=FakeLlmPort(),
            sessions=FakeSessionPort({session_id: SessionView(session_id=session_id)}),
            repository=repo,
        )
        result = await first.handle_turn(
            UserTurn(session_id=session_id, content="Hello")
        )

        second = ConversationEngine(
            llm=FakeLlmPort(),
            sessions=FakeSessionPort({session_id: SessionView(session_id=session_id)}),
            repository=repo,
        )
        again = await second.handle_turn(
            UserTurn(
                session_id=session_id,
                conversation_id=result.conversation_id,
                content="Again",
            )
        )
        assert again.user_message.sequence == 2
        assert again.assistant_message.sequence == 3
        stored = await repo.get(result.conversation_id)
        assert stored is not None
        assert [m.content for m in stored.messages] == [
            "Hello",
            "Hello there.",
            "Again",
            "Hello there.",
        ]

    async def test_end_persists_through_repository(
        self,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        engine = ConversationEngine(
            llm=FakeLlmPort(),
            sessions=FakeSessionPort({session_id: SessionView(session_id=session_id)}),
            repository=repo,
        )
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        await engine.end(result.conversation_id)
        stored = await repo.get(result.conversation_id)
        assert stored is not None
        assert stored.is_ended
        assert stored.ended_at is not None

    async def test_llm_failure_keeps_user_message(
        self,
        sqlite_session_factory: object,
        repo: ConversationPostgresRepository,
        session_id: UUID,
    ) -> None:
        llm = FakeLlmPort()
        llm.error = RuntimeError("provider down")
        engine = ConversationEngine(
            llm=llm,
            sessions=FakeSessionPort({session_id: SessionView(session_id=session_id)}),
            repository=repo,
        )
        with pytest.raises(RuntimeError, match="provider down"):
            await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))

        async with sqlite_session_factory() as db:
            rows = (
                (await db.execute(select(ConversationRecord))).scalars().all()
            )
        assert len(rows) == 1
        stored = await repo.get(rows[0].conversation_id)
        assert stored is not None
        assert [m.role for m in stored.messages] == [MessageRole.USER]
        assert stored.messages[0].content == "Hello"
        assert not stored.is_ended