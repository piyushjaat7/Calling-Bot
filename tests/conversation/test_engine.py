"""Tests of the ConversationEngine turn pipeline.

The engine is exercised through the fake session/LLM ports from
:mod:`tests.conversation.fakes`; no persistence or provider is involved.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from backend.app.conversation.context import ConversationContext, SessionView
from backend.app.conversation.conversation import ConversationClosedError
from backend.app.conversation.engine import (
    ConversationEngine,
    ConversationNotFoundError,
    SessionMismatchError,
    UnknownSessionError,
)
from backend.app.conversation.message import MessageRole
from backend.app.conversation.ports import LlmPort, SessionPort
from backend.app.conversation.schemas import UserTurn
from backend.app.conversation.state import ConversationState
from tests.conversation.fakes import FakeLlmPort, FakeSessionPort


class TestValidUserTurn:
    async def test_returns_engine_result(
        self, engine: ConversationEngine, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        assert result.session_id == session_id
        assert isinstance(result.conversation_id, UUID)
        assert result.user_message.role is MessageRole.USER
        assert result.user_message.content == "Hello"
        assert result.user_message.sequence == 0
        assert result.assistant_message.role is MessageRole.ASSISTANT
        assert result.assistant_message.content == fake_llm.response
        assert result.assistant_message.sequence == 1
        assert isinstance(result.context, ConversationContext)

    async def test_turn_without_conversation_id_creates_new_conversation(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        await engine.handle_turn(UserTurn(session_id=session_id, content="one"))
        await engine.handle_turn(UserTurn(session_id=session_id, content="two"))
        assert len(engine.conversations) == 2

    async def test_turn_with_conversation_id_continues_it(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        first = await engine.handle_turn(UserTurn(session_id=session_id, content="one"))
        second = await engine.handle_turn(
            UserTurn(
                session_id=session_id,
                conversation_id=first.conversation_id,
                content="two",
            )
        )
        assert second.conversation_id == first.conversation_id
        assert second.user_message.sequence == 2
        conversation = engine.conversations[0]
        assert [message.content for message in conversation.messages] == [
            "one",
            "Hello there.",
            "two",
            "Hello there.",
        ]

    async def test_conversation_bound_to_session(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        assert engine.conversations[0].session_id == session_id
        assert engine.conversations[0].conversation_id == result.conversation_id

    async def test_conversation_becomes_active(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        assert engine.conversations[0].state is ConversationState.ACTIVE


class TestSessionValidation:
    async def test_missing_session_raises(
        self,
        engine: ConversationEngine,
        fake_llm: FakeLlmPort,
    ) -> None:
        with pytest.raises(UnknownSessionError) as excinfo:
            await engine.handle_turn(UserTurn(session_id=uuid4(), content="Hi"))
        assert excinfo.value.session_id is not None
        assert engine.conversations == ()
        assert fake_llm.calls == []

    async def test_session_lookup_goes_through_the_port(
        self, engine: ConversationEngine, fake_sessions: FakeSessionPort, session_id: UUID
    ) -> None:
        await engine.handle_turn(UserTurn(session_id=session_id, content="Hi"))
        assert fake_sessions.lookups == [session_id]


class TestMessageAppending:
    async def test_user_message_added(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        conversation = engine.conversations[0]
        assert conversation.messages == (result.user_message, result.assistant_message)

    async def test_assistant_response_added(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        conversation = engine.conversations[0]
        assert conversation.messages[-1] is result.assistant_message
        assert result.assistant_message.content == "Hello there."


class TestLlmInteraction:
    async def test_llm_called_with_correct_context(
        self, engine: ConversationEngine, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        assert len(fake_llm.calls) == 1
        context = fake_llm.calls[0]
        assert context.session_id == session_id
        assert context.state is ConversationState.ACTIVE
        assert [message.content for message in context.messages] == ["Hello"]
        assert context.session is not None
        assert context.session.session_id == session_id

    async def test_context_never_contains_the_assistant_reply(
        self, engine: ConversationEngine, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        assert [message.content for message in fake_llm.calls[0].messages] == ["Hello"]

    async def test_llm_failure_propagates(
        self, engine: ConversationEngine, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        fake_llm.error = RuntimeError("provider boom")
        with pytest.raises(RuntimeError, match="provider boom"):
            await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        conversation = engine.conversations[0]
        assert [message.role for message in conversation.messages] == [MessageRole.USER]
        assert conversation.state is ConversationState.ACTIVE

    async def test_retry_after_llm_failure(
        self, engine: ConversationEngine, fake_llm: FakeLlmPort, session_id: UUID
    ) -> None:
        fake_llm.error = RuntimeError("provider boom")
        with pytest.raises(RuntimeError):
            await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        fake_llm.error = None
        conversation_id = engine.conversations[0].conversation_id
        result = await engine.handle_turn(
            UserTurn(
                session_id=session_id,
                conversation_id=conversation_id,
                content="Hello",
            )
        )
        assert result.user_message.sequence == 1
        assert result.assistant_message.sequence == 2


class TestConversationLifecycle:
    async def test_end_marks_conversation_ended(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        conversation = await engine.end(result.conversation_id)
        assert conversation.is_ended is True
        assert conversation.ended_at is not None

    async def test_end_unknown_conversation_raises(self, engine: ConversationEngine) -> None:
        with pytest.raises(ConversationNotFoundError):
            await engine.end(uuid4())

    async def test_ended_conversation_rejects_turn(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        await engine.end(result.conversation_id)
        with pytest.raises(ConversationClosedError):
            await engine.handle_turn(
                UserTurn(
                    session_id=session_id,
                    conversation_id=result.conversation_id,
                    content="Late message",
                )
            )

    async def test_unknown_conversation_id_raises(
        self, engine: ConversationEngine, session_id: UUID
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            await engine.handle_turn(
                UserTurn(session_id=session_id, conversation_id=uuid4(), content="Hi")
            )

    async def test_conversation_of_another_session_rejected(
        self, engine: ConversationEngine, fake_sessions: FakeSessionPort, session_id: UUID
    ) -> None:
        result = await engine.handle_turn(UserTurn(session_id=session_id, content="Hello"))
        other_session_id = uuid4()
        fake_sessions.sessions[other_session_id] = SessionView(session_id=other_session_id)
        with pytest.raises(SessionMismatchError):
            await engine.handle_turn(
                UserTurn(
                    session_id=other_session_id,
                    conversation_id=result.conversation_id,
                    content="Hi",
                )
            )


class TestFakeImplementations:
    def test_fakes_conform_to_the_ports(
        self, fake_llm: FakeLlmPort, fake_sessions: FakeSessionPort
    ) -> None:
        assert isinstance(fake_llm, LlmPort)
        assert isinstance(fake_sessions, SessionPort)