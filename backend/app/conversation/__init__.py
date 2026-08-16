"""Conversation Core domain package.

Stages 1-5 of the Conversation Core: the domain models of a conversation
(message, conversation entity, state machine, events and context) plus the
ConversationEngine orchestrator and its external ports (session/LLM
contracts). Persistence, publisher ports and any provider integration are
deliberately not implemented yet.
"""

from backend.app.conversation.context import (
    ConversationContext,
    SessionView,
    build_context,
)
from backend.app.conversation.conversation import Conversation, ConversationClosedError
from backend.app.conversation.engine import (
    ConversationEngine,
    ConversationEngineError,
    ConversationNotFoundError,
    SessionMismatchError,
    UnknownSessionError,
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
from backend.app.conversation.ports import LlmPort, LlmResponse, SessionPort
from backend.app.conversation.schemas import EngineResult, UserTurn
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
    "ConversationEngine",
    "ConversationEngineError",
    "ConversationEvent",
    "ConversationEventType",
    "ConversationNotFoundError",
    "ConversationState",
    "ConversationStateMachine",
    "EngineResult",
    "InvalidStateTransitionError",
    "LlmPort",
    "LlmResponse",
    "Message",
    "MessageRole",
    "SessionMismatchError",
    "SessionPort",
    "SessionView",
    "StateTransition",
    "UnknownSessionError",
    "UserTurn",
    "build_context",
    "created_event",
    "ended_event",
    "error_event",
    "message_appended_event",
    "started_event",
    "state_changed_event",
]