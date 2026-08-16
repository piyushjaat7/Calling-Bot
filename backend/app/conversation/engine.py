"""ConversationEngine — the async orchestrator of the Conversation Core.

The engine implements the turn pipeline:

``receive user turn -> validate session -> obtain/create conversation ->
append USER message -> build ConversationContext -> call LlmPort ->
append ASSISTANT message -> return EngineResult``

Every step delegates to the domain instead of reimplementing it: message
validation and lifecycle transitions live in ``Conversation``/``Message``
(backed by the state machine), the context snapshot comes from
:func:`~backend.app.conversation.context.build_context`, and the session
lookup happens through :class:`~backend.app.conversation.ports.SessionPort`
so the engine never touches any repository.

Conversations are held in an in-memory registry owned by the engine
instance; persistence is out of scope for this stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.app.conversation.context import SessionView, build_context
from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import Message, MessageRole
from backend.app.conversation.ports import LlmPort, LlmResponse, SessionPort
from backend.app.conversation.schemas import EngineResult, UserTurn
from backend.app.core.logger import LogContext, bind_context, get_logger

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any


class ConversationEngineError(Exception):
    """Base class of every ConversationEngine error."""


class UnknownSessionError(ConversationEngineError):
    """Raised when the session referenced by a turn does not exist.

    Attributes:
        session_id: The identifier that was looked up.
    """

    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found.")
        self.session_id: UUID = session_id


class ConversationNotFoundError(ConversationEngineError):
    """Raised when a referenced conversation is not known to the engine.

    Attributes:
        conversation_id: The identifier that was looked up.
    """

    def __init__(self, conversation_id: UUID) -> None:
        super().__init__(f"Conversation {conversation_id} not found.")
        self.conversation_id: UUID = conversation_id


class SessionMismatchError(ConversationEngineError):
    """Raised when a conversation belongs to a different session.

    Attributes:
        conversation_id: The conversation that was referenced.
        session_id: The session that does not own the conversation.
    """

    def __init__(self, conversation_id: UUID, session_id: UUID) -> None:
        super().__init__(
            f"Conversation {conversation_id} does not belong to session {session_id}."
        )
        self.conversation_id: UUID = conversation_id
        self.session_id: UUID = session_id


class ConversationEngine:
    """Async orchestrator of user turns against a conversation.

    Args:
        llm: The assistant-text generator port.
        sessions: The session lookup port.
    """

    def __init__(self, llm: LlmPort, sessions: SessionPort) -> None:
        self._llm: LlmPort = llm
        self._sessions: SessionPort = sessions
        self._conversations: dict[UUID, Conversation] = {}
        self._log: Logger = get_logger("conversation")

    @property
    def conversations(self) -> tuple[Conversation, ...]:
        """Immutable view of every conversation held by the engine."""
        return tuple(self._conversations.values())

    async def handle_turn(self, turn: UserTurn) -> EngineResult:
        """Process one user turn through the full pipeline.

        Args:
            turn: The validated user turn.

        Returns:
            The immutable record of the processed turn.

        Raises:
            UnknownSessionError: When the referenced session does not exist.
            ConversationNotFoundError: When a referenced conversation is
                unknown to the engine.
            SessionMismatchError: When the conversation belongs to another
                session.
            ConversationClosedError: When the conversation is already ended.
            Exception: Propagated from the LLM port when generation fails.
        """
        session: SessionView | None = await self._sessions.get(turn.session_id)
        if session is None:
            raise UnknownSessionError(turn.session_id)

        conversation: Conversation = self._obtain_conversation(turn)
        user_message: Message = conversation.add_message(
            MessageRole.USER, turn.content
        )
        context = build_context(conversation, session=session)
        response: LlmResponse = await self._llm.generate(context)
        assistant_message: Message = conversation.add_message(
            MessageRole.ASSISTANT, response.content
        )

        self._log_context(turn.session_id).info(
            f"User turn processed for conversation {conversation.conversation_id}"
        )
        return EngineResult(
            session_id=turn.session_id,
            conversation_id=conversation.conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            context=context,
        )

    async def end(self, conversation_id: UUID) -> Conversation:
        """End a conversation held by the engine.

        Args:
            conversation_id: The conversation to end.

        Returns:
            The ended conversation.

        Raises:
            ConversationNotFoundError: When the conversation is unknown.
            ConversationClosedError: When the conversation is already ended.
        """
        conversation: Conversation | None = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        conversation.end()
        self._log_context(conversation.session_id).info(
            f"Conversation {conversation_id} ended"
        )
        return conversation

    def _obtain_conversation(self, turn: UserTurn) -> Conversation:
        """Create a new conversation or resolve the referenced one."""
        if turn.conversation_id is not None:
            conversation = self._conversations.get(turn.conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(turn.conversation_id)
            if conversation.session_id != turn.session_id:
                raise SessionMismatchError(turn.conversation_id, turn.session_id)
            return conversation

        conversation = Conversation(session_id=turn.session_id)
        self._conversations[conversation.conversation_id] = conversation
        return conversation

    def _log_context(self, session_id: UUID) -> Logger:
        """Return the module logger bound with the session context."""
        return bind_context(self._log, LogContext(session_id=str(session_id)))


__all__ = [
    "ConversationEngine",
    "ConversationEngineError",
    "ConversationNotFoundError",
    "SessionMismatchError",
    "UnknownSessionError",
]