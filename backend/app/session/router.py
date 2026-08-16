"""Session REST endpoints.

Exposes the session lifecycle over HTTP:

* ``POST /session/start`` — create an ``ACTIVE`` session,
* ``POST /session/end`` — end a session,
* ``GET /session/{id}`` — fetch session details.

The router is deliberately *not* mounted by the application factory yet:
callers decide where it plugs in, which keeps the module independently
testable (the test suite mounts it directly on a throwaway application).
The service is injected through a FastAPI dependency; tests override it
with `app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.database import get_async_session_factory
from backend.app.session.exceptions import (
    SessionNotFoundError,
    SessionStateError,
)
from backend.app.session.repository import SessionPostgresRepository
from backend.app.session.schemas import (
    SessionData,
    SessionEndRequest,
    SessionResponse,
)
from backend.app.session.service import SessionService

#: Shared default service backed by PostgreSQL; tests replace the dependency.
_default_service: SessionService = SessionService(
    SessionPostgresRepository(get_async_session_factory())
)

#: Router carrying the session lifecycle endpoints.
router = APIRouter(prefix="/session", tags=["session"])


def get_session_service() -> SessionService:
    """FastAPI dependency providing the shared session service."""
    return _default_service


@router.post(
    "/start",
    response_model=SessionResponse,
    status_code=201,
    summary="Start a new session",
)
async def start_session(
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Create a new ``ACTIVE`` session.

    Args:
        service: The injected session service.

    Returns:
        The success envelope carrying the started session.
    """
    session = await service.start()
    return SessionResponse(
        success=True,
        message="Session started.",
        data=SessionData.from_domain(session),
    )


@router.post("/end", response_model=SessionResponse, summary="End a session")
async def end_session(
    payload: SessionEndRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """End an ``ACTIVE`` session.

    Args:
        payload: The validated request body.
        service: The injected session service.

    Returns:
        The success envelope carrying the ended session.

    Raises:
        HTTPException: ``404`` when the session is unknown, ``409`` when it
            is already ended.
    """
    try:
        session = await service.end(payload.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SessionResponse(
        success=True,
        message="Session ended.",
        data=SessionData.from_domain(session),
    )


@router.get("/{session_id}", response_model=SessionResponse, summary="Get a session")
async def get_session(
    session_id: UUID,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Return the details of a session.

    Args:
        session_id: The session identifier (validated as a UUID).
        service: The injected session service.

    Returns:
        The success envelope carrying the session.

    Raises:
        HTTPException: ``404`` when the session is unknown.
    """
    try:
        session = await service.get(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SessionResponse(
        success=True,
        message="Session found.",
        data=SessionData.from_domain(session),
    )


__all__ = ["get_session_service", "router"]