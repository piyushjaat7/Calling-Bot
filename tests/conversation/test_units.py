"""Unit tests for the conversation package.

These tests exercise the pure domain (stage 1-4) — no Session, LLM, ports,
database or FastAPI involvement.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID, uuid4

import pytest

from backend.app.conversation.context import (
    RECENT_MESSAGE_WINDOW,
    ConversationContext,
    SessionView,
    build_context,
)
from backend.app.conversation.conversation import (
    Conversation,
    ConversationClosedError,
)
from backend.app.conversation.events import (
    ConversationCorrelation,
    ConversationEvent,
    ConversationEventType,
    created_event,
    ended_event,
    error_event,
    message_appended_event,
    started_event,
    state_changed_event,
)
from backend.app.conversation.message import MAX_MESSAGE_CHARS, Message, MessageRole
from backend.app.conversation.state import (
    STATE_MACHINE,
    ConversationState,
    ConversationStateMachine,
    InvalidStateTransitionError,
    StateTransition,
)

# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class TestMessage:
    def test_valid_creation(self) -> None:
        cid = uuid4()
        msg = Message(
            conversation_id=cid,
            sequence=0,
            role=MessageRole.USER,
            content="hello",
        )
        assert isinstance(msg.message_id, UUID)
        assert msg.conversation_id == cid
        assert msg.sequence == 0
        assert msg.role is MessageRole.USER
        assert msg.content == "hello"
        assert isinstance(msg.created_at, datetime)
        assert msg.created_at.tzinfo is UTC
        assert isinstance(msg.metadata, MappingProxyType)
        assert dict(msg.metadata) == {}

    def test_all_roles_valid(self) -> None:
        for role in MessageRole:
            msg = Message(
                conversation_id=uuid4(),
                sequence=0,
                role=role,
                content="x",
            )
            assert msg.role is role

    def test_content_must_not_be_empty(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            Message(conversation_id=uuid4(), sequence=0, role=MessageRole.USER, content="")

    def test_content_must_not_be_blank(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            Message(
                conversation_id=uuid4(),
                sequence=0,
                role=MessageRole.USER,
                content="  \t ",
            )

    def test_content_must_be_string(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            Message(  # type: ignore[arg-type]
                conversation_id=uuid4(),
                sequence=0,
                role=MessageRole.USER,
                content=12345,
            )

    def test_negative_sequence_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Message(
                conversation_id=uuid4(),
                sequence=-1,
                role=MessageRole.USER,
                content="x",
            )

    def test_max_length_boundary_accepted(self) -> None:
        content = "a" * MAX_MESSAGE_CHARS
        msg = Message(
            conversation_id=uuid4(), sequence=0, role=MessageRole.USER, content=content
        )
        assert len(msg.content) == MAX_MESSAGE_CHARS

    def test_overflow_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="exceeds the limit"):
            Message(
                conversation_id=uuid4(),
                sequence=0,
                role=MessageRole.USER,
                content="a" * (MAX_MESSAGE_CHARS + 1),
            )

    def test_immutable(self) -> None:
        msg = Message(
            conversation_id=uuid4(),
            sequence=0,
            role=MessageRole.USER,
            content="hello",
        )
        with pytest.raises(FrozenInstanceError):
            msg.content = "other"  # type: ignore[misc]

    def test_metadata_is_immutable_mapping(self) -> None:
        original = {"request_id": "req-1"}
        msg = Message(
            conversation_id=uuid4(),
            sequence=0,
            role=MessageRole.USER,
            content="hello",
            metadata=original,
        )
        assert isinstance(msg.metadata, MappingProxyType)
        assert msg.metadata["request_id"] == "req-1"
        # Mutating the source dict afterwards must not affect the message.
        original["request_id"] = "mutated"
        assert msg.metadata["request_id"] == "req-1"
        with pytest.raises(TypeError):
            msg.metadata["request_id"] = "other"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class TestConversation:
    def test_creation_defaults(self) -> None:
        sid = uuid4()
        conv = _conversation(sid)
        assert conv.session_id == sid
        assert isinstance(conv.conversation_id, UUID)
        assert conv.state is ConversationState.CREATED
        assert conv.messages == ()
        assert conv.transitions == ()
        assert conv.is_ended is False
        assert conv.ended_at is None
        assert isinstance(conv.created_at, datetime)
        assert isinstance(conv.updated_at, datetime)
        assert conv.created_at.tzinfo is UTC

    def test_conversation_identity_is_generated(self) -> None:
        conv = _conversation()
        assert isinstance(conv.conversation_id, UUID)

    def test_session_relationship_is_one_many(self) -> None:
        """A session may own several conversations (no enforced 1:1)."""
        sid = uuid4()
        first = _conversation(sid)
        second = _conversation(sid)
        assert first.session_id == second.session_id == sid
        assert first.conversation_id != second.conversation_id

    def test_metadata_accepted(self) -> None:
        conv = _conversation(metadata={"channel": "phone"})
        assert conv.metadata["channel"] == "phone"
        assert isinstance(conv.metadata, MappingProxyType)

    def test_initial_state_is_created(self) -> None:
        assert _conversation().state is ConversationState.CREATED

    def test_add_message_assigns_sequences(self) -> None:
        conv = _conversation()
        first = _speak(conv, MessageRole.USER, "one")
        second = _speak(conv, MessageRole.ASSISTANT, "two")
        third = _speak(conv, MessageRole.USER, "three")
        assert (first.sequence, second.sequence, third.sequence) == (0, 1, 2)
        assert [m.content for m in conv.messages] == ["one", "two", "three"]

    def test_ordering_follows_sequence_not_timestamp(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "first")
        _speak(conv, MessageRole.USER, "second")
        _speak(conv, MessageRole.USER, "third")
        sequences = [msg.sequence for msg in conv.messages]
        assert sequences == sorted(sequences) == [0, 1, 2]

    def test_first_message_starts_conversation(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "hi")
        assert conv.state is ConversationState.ACTIVE
        assert len(conv.transitions) == 1
        transition = conv.transitions[0]
        assert transition.current is ConversationState.CREATED
        assert transition.target is ConversationState.ACTIVE

    def test_messages_are_immutable_after_append(self) -> None:
        conv = _conversation()
        msg = _speak(conv, MessageRole.USER, "hi")
        with pytest.raises(FrozenInstanceError):
            msg.content = "boom"  # type: ignore[misc]

    def test_start_explicitly(self) -> None:
        conv = _conversation()
        conv.start()
        assert conv.state is ConversationState.ACTIVE

    def test_end_from_created(self) -> None:
        conv = _conversation()
        conv.end()
        assert conv.state is ConversationState.ENDED
        assert conv.is_ended is True
        assert conv.ended_at is not None

    def test_end_from_active(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "hi")
        conv.end()
        assert conv.state is ConversationState.ENDED
        assert conv.ended_at is not None
        assert conv.transitions[-1].target is ConversationState.ENDED

    def test_end_twice_raises(self) -> None:
        conv = _conversation()
        conv.end()
        with pytest.raises(ConversationClosedError):
            conv.end()

    def test_add_message_after_end_raises(self) -> None:
        conv = _conversation()
        conv.end()
        with pytest.raises(ConversationClosedError):
            conv.add_message(MessageRole.USER, "late", metadata={})

    def test_start_after_end_raises_state_error(self) -> None:
        conv = _conversation()
        conv.end()
        with pytest.raises(InvalidStateTransitionError):
            conv.start()

    def test_start_again_is_allowed_self_loop(self) -> None:
        """ACTIVE -> ACTIVE is a legal table entry; a second start() is a no-op."""
        conv = _conversation()
        conv.start()
        conv.start()
        assert conv.state is ConversationState.ACTIVE
        assert conv.transitions[-1].current is ConversationState.ACTIVE
        assert conv.transitions[-1].target is ConversationState.ACTIVE

    def test_state_never_rewinds(self) -> None:
        conv = _conversation()
        conv.start()
        conv.end()
        with pytest.raises(ConversationClosedError):
            _speak(conv, MessageRole.USER, "still there")


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestStateMachine:
    machine: ConversationStateMachine = STATE_MACHINE

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (ConversationState.CREATED, ConversationState.ACTIVE),
            (ConversationState.CREATED, ConversationState.ENDED),
            (ConversationState.ACTIVE, ConversationState.ACTIVE),
            (ConversationState.ACTIVE, ConversationState.ENDED),
        ],
    )
    def test_valid_transitions(
        self, current: ConversationState, target: ConversationState
    ) -> None:
        assert self.machine.can_transition(current, target)
        transition = self.machine.transition(current, target)
        assert isinstance(transition, StateTransition)
        assert transition.current is current
        assert transition.target is target
        assert isinstance(transition.occurred_at, datetime)
        assert transition.occurred_at.tzinfo is UTC

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (ConversationState.CREATED, ConversationState.CREATED),
            (ConversationState.CREATED, ConversationState.SUSPENDED),
            (ConversationState.ACTIVE, ConversationState.CREATED),
            (ConversationState.ACTIVE, ConversationState.SUSPENDED),
            (ConversationState.SUSPENDED, ConversationState.ACTIVE),
            (ConversationState.SUSPENDED, ConversationState.ENDED),
            (ConversationState.SUSPENDED, ConversationState.SUSPENDED),
            (ConversationState.ENDED, ConversationState.CREATED),
            (ConversationState.ENDED, ConversationState.ACTIVE),
            (ConversationState.ENDED, ConversationState.SUSPENDED),
            (ConversationState.ENDED, ConversationState.ENDED),
        ],
    )
    def test_invalid_transitions(
        self, current: ConversationState, target: ConversationState
    ) -> None:
        assert not self.machine.can_transition(current, target)
        with pytest.raises(InvalidStateTransitionError) as excinfo:
            self.machine.transition(current, target)
        assert excinfo.value.current is current
        assert excinfo.value.target is target

    def test_ended_is_terminal(self) -> None:
        assert self.machine.is_terminal(ConversationState.ENDED)
        for state in (
            ConversationState.CREATED,
            ConversationState.ACTIVE,
            ConversationState.SUSPENDED,
        ):
            assert not self.machine.is_terminal(state)

    def test_valid_targets_per_state(self) -> None:
        assert self.machine.valid_targets(ConversationState.CREATED) == frozenset(
            {ConversationState.ACTIVE, ConversationState.ENDED}
        )
        assert self.machine.valid_targets(ConversationState.ACTIVE) == frozenset(
            {ConversationState.ACTIVE, ConversationState.ENDED}
        )
        assert self.machine.valid_targets(ConversationState.SUSPENDED) == frozenset()
        assert self.machine.valid_targets(ConversationState.ENDED) == frozenset()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TestEvents:
    def _active_conversation(self) -> Conversation:
        conv = _conversation()
        conv.start()
        return conv

    def test_conversation_created_event(self) -> None:
        conv = _conversation()
        event = created_event(conv)
        assert isinstance(event, ConversationEvent)
        assert event.type is ConversationEventType.CONVERSATION_CREATED
        assert event.conversation_id == conv.conversation_id
        assert event.session_id == conv.session_id
        assert event.payload == {"state": "created"}
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.occurred_at, datetime)

    def test_started_event(self) -> None:
        conv = _conversation()
        conv.start()
        event = started_event(conv)
        assert event.type is ConversationEventType.CONVERSATION_STARTED
        assert event.payload == {"state": "active"}

    def test_message_appended_event(self) -> None:
        conv = _conversation()
        msg = _speak(conv, MessageRole.USER, "hello there")
        event = message_appended_event(conv, msg)
        assert event.type is ConversationEventType.MESSAGE_APPENDED
        assert event.payload["sequence"] == 0
        assert event.payload["role"] == "user"
        assert event.payload["message"] == "hello there"
        assert event.payload["message_id"] == str(msg.message_id)

    def test_state_changed_event(self) -> None:
        conv = _conversation()
        transition = conv.start()
        event = state_changed_event(conv, transition)
        assert event.type is ConversationEventType.STATE_CHANGED
        assert event.payload == {"from_state": "created", "to_state": "active"}
        assert event.occurred_at == transition.occurred_at

    def test_ended_event(self) -> None:
        conv = _conversation()
        conv.start()
        conv.end()
        event = ended_event(conv)
        assert event.type is ConversationEventType.CONVERSATION_ENDED
        assert event.payload["state"] == "ended"
        assert event.payload["ended_at"] is not None

    def test_error_event_is_sanitized(self) -> None:
        event = error_event(
            conversation_id=uuid4(),
            session_id=uuid4(),
            message="llm unavailable",
        )
        assert event.type is ConversationEventType.CONVERSATION_ERROR
        assert event.payload == {"error": "llm unavailable"}
        # No exception object, no traceback, only plain strings.
        assert all(isinstance(v, str) for v in event.payload.values())

    def test_correlation_carried(self) -> None:
        conv = _conversation()
        correlation = ConversationCorrelation(
            request_id="req-1", caller_id="caller-1"
        )
        event = created_event(conv, correlation)
        assert event.correlation is correlation
        assert event.correlation.request_id == "req-1"
        assert event.correlation.caller_id == "caller-1"

    def test_default_event_correlation(self) -> None:
        event = created_event(_conversation())
        assert isinstance(event.correlation, ConversationCorrelation)
        assert event.correlation.request_id is None

    def test_event_identity_unique(self) -> None:
        conv = _conversation()
        ids = {created_event(conv).event_id for _ in range(10)}
        assert len(ids) == 10

    def test_event_payload_is_immutable_mapping(self) -> None:
        conv = _conversation()
        event = created_event(conv)
        assert isinstance(event.payload, MappingProxyType)
        with pytest.raises(TypeError):
            event.payload["state"] = "active"  # type: ignore[index]

    def test_event_is_immutable(self) -> None:
        conv = _conversation()
        event = created_event(conv)
        with pytest.raises(FrozenInstanceError):
            event.type = ConversationEventType.CONVERSATION_STARTED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class TestContext:
    def test_context_basics(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "hello")
        context = build_context(conv)
        assert isinstance(context, ConversationContext)
        assert context.conversation_id == conv.conversation_id
        assert context.session_id == conv.session_id
        assert context.state is ConversationState.ACTIVE

    def test_context_contains_recent_messages_only(self) -> None:
        conv = _conversation()
        total = RECENT_MESSAGE_WINDOW + 5
        for index in range(total):
            _speak(conv, MessageRole.USER, f"m{index}")
        context = build_context(conv)
        assert len(context.messages) == RECENT_MESSAGE_WINDOW
        assert context.messages[0].content == "m5"
        assert context.messages[-1].content == f"m{total - 1}"
        # Window retains sequence ordering.
        sequences = [msg.sequence for msg in context.messages]
        assert sequences == sorted(sequences)

    def test_context_under_window_returns_all(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "only")
        context = build_context(conv)
        assert [msg.content for msg in context.messages] == ["only"]

    def test_turn_count_counts_user_messages(self) -> None:
        conv = _conversation()
        _speak(conv, MessageRole.USER, "one")
        _speak(conv, MessageRole.ASSISTANT, "two")
        _speak(conv, MessageRole.USER, "three")
        context = build_context(conv)
        assert context.turn_count == 2

    def test_session_view_attached(self) -> None:
        conv = _conversation()
        view = SessionView(
            session_id=conv.session_id,
            caller_id="caller-1",
            channel="phone",
            status="active",
            metadata={"region": "in"},
        )
        context = build_context(conv, session=view)
        assert context.session is view
        assert context.session is not None
        assert context.session.caller_id == "caller-1"
        assert context.session.channel == "phone"
        assert context.session.metadata["region"] == "in"

    def test_session_view_defaults(self) -> None:
        view = SessionView(session_id=uuid4())
        assert view.status == "unknown"
        assert view.caller_id is None
        assert view.channel is None
        assert isinstance(view.metadata, MappingProxyType)

    def test_reserved_slots_empty_by_default(self) -> None:
        context = build_context(_conversation())
        assert context.memory_excerpts == ()
        assert context.tool_results == ()

    def test_reserved_slots_accept_values(self) -> None:
        context = build_context(
            _conversation(),
            memory_excerpts=("remember this",),
            tool_results=("calendar: ok",),
        )
        assert context.memory_excerpts == ("remember this",)
        assert context.tool_results == ("calendar: ok",)

    def test_context_is_immutable(self) -> None:
        context = build_context(_conversation())
        with pytest.raises(FrozenInstanceError):
            context.turn_count = 99  # type: ignore[misc]

    def test_context_has_no_llm_specific_fields(self) -> None:
        names = {f.name for f in fields(ConversationContext)}
        assert "prompt" not in names
        assert "provider" not in names
        assert "model" not in names
        assert "system_instruction" not in names
        # Only structured domain/session data is present.
        assert {"conversation_id", "session_id", "state", "messages", "turn_count"} <= names


def _conversation(
    session_id: UUID | None = None, metadata: dict[str, str] | None = None
) -> Conversation:
    """Create a conversation bound to an optional session id."""
    return Conversation(session_id=session_id or uuid4(), metadata=metadata or {})


def _speak(conv: Conversation, role: MessageRole, content: str) -> Message:
    """Append a message with an explicit (empty) metadata mapping."""
    return conv.add_message(role, content, metadata={})