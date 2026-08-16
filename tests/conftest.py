"""Shared fixtures of the whole test suite.

Provides an isolated in-memory SQLite database (``sqlite+aiosqlite`` with a
static pool) whose schema mirrors the PostgreSQL production schema. The
PostgreSQL-backed repositories run against it, so persistence tests exercise
real SQL round-trips (including foreign keys) without requiring a running
PostgreSQL server.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from backend.app.database import Base


@pytest.fixture
async def sqlite_engine() -> AsyncIterator[AsyncEngine]:
    """An in-memory SQLite engine with the schema created and FKs enforced."""
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def sqlite_session_factory(
    sqlite_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """An async session factory bound to the isolated SQLite engine."""
    return async_sessionmaker(sqlite_engine, expire_on_commit=False)