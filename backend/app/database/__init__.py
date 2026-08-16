"""Database infrastructure layer.

SQLAlchemy engine/session management and the ORM records for persisting
sessions, conversations and messages. Domain models in the ``session`` and
``conversation`` packages never import SQLAlchemy; repositories translate
between the ORM records and the domain objects.
"""

from backend.app.database.engine import (
    get_async_session_factory,
    get_engine,
    init_database,
)
from backend.app.database.models import (
    Base,
    ConversationRecord,
    MessageRecord,
    SessionRecord,
    UtcDateTime,
)

__all__ = [
    "Base",
    "ConversationRecord",
    "MessageRecord",
    "SessionRecord",
    "UtcDateTime",
    "get_async_session_factory",
    "get_engine",
    "init_database",
]