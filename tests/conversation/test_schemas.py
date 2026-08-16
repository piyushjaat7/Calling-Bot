"""Tests of the Conversation Engine schemas."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from backend.app.conversation.context import build_context
from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import MessageRole
from backend.app.conversation.schemas import EngineResult, UserTurn


class TestUserTurn:
    def test_valid_turn_without_conversation(self) -> None:
        session_id = uuid4()
        turn = UserTurn(session_id=session_id, content="Hello")
        assert turn.session_id == session_id
        assert turn.conversation_id is None
        assert turn.content == "Hello"

    def test_valid_turn_with_conversation_id(self) -> None:
        session_id = uuid4()
        conversation_id = uuid4()
        turn = UserTurn(
            session_id=session_id,
            conversation_id=conversation_id,
            content="Hello",
        )
        assert turn.conversation_id == conversation_id

    def test_invalid_session_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserTurn(session_id="not-a-uuid", content="Hello")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserTurn(session_id=uuid4(), content="")

    def test_missing_session_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserTurn(content="Hello")

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserTurn(session_id=uuid4(), content="Hello", extra=True)


class TestEngineResult:
    def test_holds_turn_artifacts(self) -> None:
        session_id = uuid4()
        conversation = Conversation(session_id=session_id)
        user_message = conversation.add_message(MessageRole.USER, "Hello")
        assistant_message = conversation.add_message(MessageRole.ASSISTANT, "Hi there.")
        context = build_context(conversation)

        result = EngineResult(
            session_id=session_id,
            conversation_id=conversation.conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            context=context,
        )
        assert result.session_id == session_id
        assert result.conversation_id == conversation.conversation_id
        assert result.user_message is user_message
        assert result.assistant_message is assistant_message
        assert result.context is context
        assert isinstance(result.session_id, UUID)
        assert isinstance(result.conversation_id, UUID)

    def test_is_immutable(self) -> None:
        conversation = Conversation(session_id=uuid4())
        user_message = conversation.add_message(MessageRole.USER, "Hello")
        assistant_message = conversation.add_message(MessageRole.ASSISTANT, "Hi there.")
        context = build_context(conversation)
        result = EngineResult(
            session_id=conversation.session_id,
            conversation_id=conversation.conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            context=context,
        )
        with pytest.raises(FrozenInstanceError):
            result.session_id = uuid4()  # type: ignore[misc]