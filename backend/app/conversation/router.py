"""Conversation REST endpoints.

Exposes the Conversation Engine over HTTP:

* ``POST /conversation/turn`` — process one user turn end-to-end (session
  validation -> conversation -> LlmPort -> assistant reply).

The router only translates HTTP input/output and delegates to the engine;
no business logic lives here. The engine is injected through a FastAPI
dependency and replaced by tests with ``app.dependency_overrides``.

The default engine is wired through the real ports: the shared session
service (the same instance the Session router uses, backed by PostgreSQL)
and the local Ollama adapter behind the ``LlmPort``, with a PostgreSQL
conversation repository behind the persistence port.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.conversation.conversation import ConversationClosedError
from backend.app.conversation.engine import (
    ConversationEngine,
    ConversationNotFoundError,
    SessionMismatchError,
    UnknownSessionError,
)
from backend.app.conversation.repository import ConversationPostgresRepository
from backend.app.conversation.schemas import TurnResponse, UserTurn
from backend.app.database import get_async_session_factory
from backend.app.llm.exceptions import LlmError
from backend.app.llm.ollama import OllamaAdapter
from backend.app.session.router import get_session_service
from backend.app.session.session_port import ServiceSessionPort

#: Shared default engine: real ports (PostgreSQL sessions + local Ollama).
_default_engine: ConversationEngine = ConversationEngine(
    llm=OllamaAdapter(),
    sessions=ServiceSessionPort(get_session_service()),
    repository=ConversationPostgresRepository(get_async_session_factory()),
)

#: Router carrying the conversation endpoints.
router = APIRouter(prefix="/conversation", tags=["conversation"])


def get_conversation_engine() -> ConversationEngine:
    """FastAPI dependency providing the shared conversation engine."""
    return _default_engine


@router.post(
    "/turn",
    response_model=TurnResponse,
    summary="Process a user turn",
)
async def process_turn(
    payload: UserTurn,
    engine: Annotated[ConversationEngine, Depends(get_conversation_engine)],
) -> TurnResponse:
    """Process one user turn and return the assistant reply.

    Args:
        payload: The validated user turn.
        engine: The injected conversation engine.

    Returns:
        The success envelope carrying the processed turn.

    Raises:
        HTTPException: ``404`` when the session or conversation is unknown,
            ``409`` when the conversation is already ended or belongs to
            another session, ``422`` for invalid turn content, ``502`` when
            the LLM provider fails.
    """
    try:
        result = await engine.handle_turn(payload)
    except UnknownSessionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConversationClosedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TurnResponse.from_result(result)


__all__ = ["get_conversation_engine", "router"]