"""SQLAlchemy ORM records of the persistence layer.

These mapped classes are the *storage* shape of the Session and Conversation
domains. They are deliberately kept free of business logic — the domain
entities in :mod:`backend.app.session` and :mod:`backend.app.conversation`
never import SQLAlchemy; repositories translate between the records here
and the domain objects.

Conventions preserved from the domain:

* UUID identifiers (native on PostgreSQL),
* timezone-aware UTC timestamps (normalized by :class:`UtcDateTime`, which
  also fixes the naive datetimes returned by SQLite in tests),
* session/conversation state stored as plain strings (the StrEnum values),
* message ordering by ``sequence`` with a unique per-conversation
  constraint.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

#: JSON column storage: native JSONB on PostgreSQL, generic JSON elsewhere
#: (SQLite in the test suite).
_JSON: Any = JSON().with_variant(JSONB, "postgresql")


class UtcDateTime(TypeDecorator):
    """DateTime that always round-trips as a timezone-aware UTC value.

    PostgreSQL's ``TIMESTAMPTZ`` already returns aware datetimes; SQLite
    returns naive ones. This decorator normalizes both on the way in and on
    the way out so repositories always hand aware UTC datetimes to the
    domain models (which enforce that invariant).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        """Normalize a naive value to aware UTC before binding."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        """Normalize a naive value read from storage to aware UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base of every ORM record."""


class SessionRecord(Base):
    """Storage record of a session (mirrors the Session domain entity)."""

    __tablename__ = "sessions"

    session_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class ConversationRecord(Base):
    """Storage record of a conversation lifecycle row."""

    __tablename__ = "conversations"

    conversation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    # ``metadata`` is reserved by the Declarative API -> attribute is
    # ``metadata_``, physical column stays ``metadata``.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", _JSON, nullable=False, default=dict
    )


class MessageRecord(Base):
    """Storage record of one conversation message (sequence-ordered)."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence", name="uq_conversation_messages_sequence"
        ),
    )

    message_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", _JSON, nullable=False, default=dict
    )


__all__ = [
    "Base",
    "ConversationRecord",
    "MessageRecord",
    "SessionRecord",
    "UtcDateTime",
]