"""Shared fixtures of the Conversation Engine tests.

Provides a known session identifier, the fake session/LLM ports from
:mod:`tests.conversation.fakes` and an engine wired to them, so every engine
behavior can be exercised without any provider or database.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from backend.app.conversation.context import SessionView
from backend.app.conversation.engine import ConversationEngine
from tests.conversation.fakes import FakeLlmPort, FakeSessionPort


@pytest.fixture
def session_id() -> UUID:
    """A known session identifier present in the fake session port."""
    return uuid4()


@pytest.fixture
def fake_sessions(session_id: UUID) -> FakeSessionPort:
    """A fake session port knowing exactly one session."""
    return FakeSessionPort({session_id: SessionView(session_id=session_id)})


@pytest.fixture
def fake_llm() -> FakeLlmPort:
    """A fake LLM port returning a fixed assistant response."""
    return FakeLlmPort()


@pytest.fixture
def engine(
    fake_llm: FakeLlmPort, fake_sessions: FakeSessionPort
) -> ConversationEngine:
    """A ConversationEngine wired to the fake ports."""
    return ConversationEngine(llm=fake_llm, sessions=fake_sessions)