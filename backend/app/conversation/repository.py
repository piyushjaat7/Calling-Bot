"""PostgreSQL-backed ``ConversationRepository`` implementation.

The repository is a thin translation layer between the
:class:`~backend.app.conversation.ports.ConversationRepository` contract
and the SQLAlchemy records in :mod:`backend.app.database`:

* :meth:`ConversationPostgresRepository.get` hydrates a domain
  :class:`~backend.app.conversation.conversation.Conversation` (with every
  message, in sequence order) from the stored rows,
* :meth:`ConversationPostgresRepository.save` persists the conversation
  lifecycle row and appends any message not yet stored (idempotent:
  re-saving the same conversation never duplicates rows).

Domain objects stay SQLAlchemy-free; hydration relies on the dataclass
field contract and ``object.__setattr__`` for the ``init=False`` private
fields. The same code runs against PostgreSQL in production and against
SQLite (``sqlite+aiosqlite``) in the isolated test suite.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.conversation.conversation import Conversation
from backend.app.conversation.message import Message, MessageRole
from backend.app.conversation.state import ConversationState
from backend.app.database.models import (
    ConversationRecord,
    MessageRecord,
)


class ConversationPostgresRepository:
    """Async ``ConversationRepository`` backed by PostgreSQL (SQLAlchemy).

    Args:
        session_factory: An ``async_sessionmaker`` bound to the database
            engine.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get(self, conversation_id: UUID) -> Conversation | None:
        """Return the stored conversation, or ``None`` when unknown.

        The hydrated conversation carries every stored message in sequence
        order.

        Args:
            conversation_id: The conversation to load.

        Returns:
            The hydrated conversation when it exists, ``None`` otherwise.
        """
        async with self._session_factory() as db:
            row: ConversationRecord | None = await db.get(
                ConversationRecord, conversation_id
            )
            if row is None:
                return None
            message_rows = (
                (
                    await db.execute(
                        select(MessageRecord)
                        .where(MessageRecord.conversation_id == conversation_id)
                        .order_by(MessageRecord.sequence)
                    )
                )
                .scalars()
                .all()
            )
        return self._to_domain(row, list(message_rows))

    async def save(self, conversation: Conversation) -> None:
        """Persist the conversation row and append any missing messages.

        Idempotent: rows whose ``message_id`` is already stored are left
        untouched, so re-saving a conversation never duplicates messages.

        Args:
            conversation: The conversation to persist.
        """
        async with self._session_factory() as db, db.begin():
            row: ConversationRecord | None = await db.get(
                ConversationRecord, conversation.conversation_id
            )
            if row is None:
                db.add(self._to_record(conversation))
                await db.flush()
            else:
                self._apply_to_record(row, conversation)

            stored_ids: set[UUID] = set(
                (
                    await db.execute(
                        select(MessageRecord.message_id).where(
                            MessageRecord.conversation_id
                            == conversation.conversation_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            for message in conversation.messages:
                if message.message_id not in stored_ids:
                    db.add(
                        self._to_message_record(
                            conversation.conversation_id, message
                        )
                    )

    # -- Record <-> domain translation --------------------------------------

    @staticmethod
    def _to_record(conversation: Conversation) -> ConversationRecord:
        """Map a fresh domain conversation onto its lifecycle record."""
        return ConversationRecord(
            conversation_id=conversation.conversation_id,
            session_id=conversation.session_id,
            state=conversation.state.value,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            ended_at=conversation.ended_at,
            metadata_=dict(conversation.metadata),
        )

    @staticmethod
    def _apply_to_record(
        row: ConversationRecord, conversation: Conversation
    ) -> None:
        """Overwrite an existing lifecycle row with the domain values."""
        row.session_id = conversation.session_id
        row.state = conversation.state.value
        row.created_at = conversation.created_at
        row.updated_at = conversation.updated_at
        row.ended_at = conversation.ended_at
        row.metadata_ = dict(conversation.metadata)

    @staticmethod
    def _to_message_record(
        conversation_id: UUID, message: Message
    ) -> MessageRecord:
        """Map one domain message onto its storage record."""
        return MessageRecord(
            message_id=message.message_id,
            conversation_id=conversation_id,
            sequence=message.sequence,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
            metadata_=dict(message.metadata),
        )

    @staticmethod
    def _to_domain(
        row: ConversationRecord, message_rows: list[MessageRecord]
    ) -> Conversation:
        """Rebuild the domain conversation from its stored rows.

        The private ``init=False`` dataclass fields (state, messages,
        timestamps) are restored with ``object.__setattr__``; the
        transition log is intentionally not reconstructed (it is a
        per-instance record, not persisted state).
        """
        conversation: Conversation = Conversation(
            session_id=row.session_id,
            conversation_id=row.conversation_id,
            metadata=dict(row.metadata_),
        )
        object.__setattr__(conversation, "_state", ConversationState(row.state))
        object.__setattr__(conversation, "_created_at", row.created_at)
        object.__setattr__(conversation, "_updated_at", row.updated_at)
        object.__setattr__(conversation, "_ended_at", row.ended_at)
        object.__setattr__(
            conversation,
            "_messages",
            [
                Message(
                    conversation_id=message_row.conversation_id,
                    sequence=message_row.sequence,
                    role=MessageRole(message_row.role),
                    content=message_row.content,
                    created_at=message_row.created_at,
                    message_id=message_row.message_id,
                    metadata=dict(message_row.metadata_),
                )
                for message_row in message_rows
            ],
        )
        return conversation


__all__ = ["ConversationPostgresRepository"]