"""Conversation Core domain package.

Stages 1-4 of the Conversation Core: the domain models of a conversation
(message, conversation entity, state machine, events and context). The
engine orchestrator and the external ports (session/LLM/publisher contracts)
are deliberately not implemented yet.
"""

from backend.app.conversation.context import (
    ConversationContext,
    SessionView,
    build_context,
)
from backend.app.conversation.conversation import Conversation, ConversationClosedError
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

__all__ = [
    "MAX_MESSAGE_CHARS",
    "STATE_MACHINE",
    "Conversation",
    "ConversationClosedError",
    "ConversationContext",
    "ConversationCorrelation",
    "ConversationEvent",
    "ConversationEventType",
    "ConversationState",
    "ConversationStateMachine",
    "InvalidStateTransitionError",
    "Message",
    "MessageRole",
    "SessionView",
    "StateTransition",
    "build_context",
    "created_event",
    "ended_event",
    "error_event",
    "message_appended_event",
    "started_event",
    "state_changed_event",
]