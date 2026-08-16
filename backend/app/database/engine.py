"""Database engine and session factory.

Owns the process-wide SQLAlchemy async engine (created lazily from the
validated :class:`~backend.app.config.settings.Settings`) and the
``async_sessionmaker`` used by every PostgreSQL repository. Table
initialization for the MVP runs through :func:`init_database` (``create_all``
— idempotent); Alembic migrations are the planned successor for schema
evolution.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.config.settings import Settings, get_settings
from backend.app.database.models import Base

#: Process-wide engine singleton (creation is lazy, no connection is made
#: until the first use).
_engine: AsyncEngine | None = None


def get_engine(config: Settings | None = None) -> AsyncEngine:
    """Return the process-wide async engine, creating it once.

    Args:
        config: Optional validated settings; defaults to the global
            singleton. The engine is created exactly once per process and
            configured from ``database_*`` settings.

    Returns:
        The shared ``AsyncEngine``.
    """
    global _engine
    if _engine is None:
        settings: Settings = config if config is not None else get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            echo=settings.database_echo,
        )
    return _engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to the shared engine.

    Returns:
        A session factory that yields one transaction-scoped
        :class:`AsyncSession` per checkout.
    """
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def init_database(engine: AsyncEngine) -> None:
    """Create every missing table (MVP initialization, idempotent).

    Args:
        engine: The engine to create the schema on.

    Raises:
        Exception: Propagated from the connection when the database is
            unreachable or the schema cannot be created.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


__all__ = ["get_async_session_factory", "get_engine", "init_database"]