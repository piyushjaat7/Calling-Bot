"""Session request/response schemas.

Strict, validated Pydantic models exposing the session domain to the HTTP
layer. Request bodies reject unknown fields and malformed identifiers;
responses serialize only the documented envelope and never leak internal
domain details.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.session.model import Session, SessionStatus


class SessionEndRequest(BaseModel):
    """Payload of ``POST /session/end``."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class SessionData(BaseModel):
    """Serialized view of a session.

    Built directly from the domain :class:`Session` via
    :meth:`SessionData.from_domain`.
    """

    model_config = ConfigDict(strict=True, extra="forbid", from_attributes=True)

    session_id: UUID
    start_time: datetime
    end_time: datetime | None
    status: SessionStatus

    @classmethod
    def from_domain(cls, session: Session) -> SessionData:
        """Build the serialized view from a domain session.

        Args:
            session: The domain session to serialize.

        Returns:
            The validated data view of the session.
        """
        return cls.model_validate(session)


class SessionResponse(BaseModel):
    """Success envelope returned by every session endpoint."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    message: str
    data: SessionData


__all__ = ["SessionData", "SessionEndRequest", "SessionResponse"]