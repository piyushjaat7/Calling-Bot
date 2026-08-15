"""Session Management module.

A session is the lifecycle identity of one interaction between the platform
and an external caller (a phone call, a web chat, an API client). This
package provides:

* the persistence-independent domain model and its exceptions,
* an async repository abstraction (``Protocol``) with an in-memory
  implementation,
* the application service that orchestrates the use-cases,
* the REST endpoints exposing the lifecycle over HTTP.

The module is deliberately free of LLM, conversation-engine and database
code: the repository boundary is where any future persistence plugs in, and
the Conversation Core stays untouched.
"""

from backend.app.session.exceptions import (
    SessionError,
    SessionNotFoundError,
    SessionStateError,
)
from backend.app.session.model import Session, SessionStatus, utc_now
from backend.app.session.repository import (
    SessionInMemoryRepository,
    SessionRepository,
)
from backend.app.session.router import get_session_service, router
from backend.app.session.schemas import SessionData, SessionEndRequest, SessionResponse
from backend.app.session.service import SessionService

__all__ = [
    "Session",
    "SessionData",
    "SessionEndRequest",
    "SessionError",
    "SessionInMemoryRepository",
    "SessionNotFoundError",
    "SessionRepository",
    "SessionResponse",
    "SessionService",
    "SessionStateError",
    "SessionStatus",
    "get_session_service",
    "router",
    "utc_now",
]