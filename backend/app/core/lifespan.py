"""Application lifespan manager.

This module owns the FastAPI application lifecycle: everything that must
happen exactly once before the server starts accepting traffic and exactly
once after it stops is orchestrated here.

It is deliberately pure *orchestration*: no business logic, no database,
Redis, AI, STT/TTS, telephony or tool implementations are defined here.
Instead, every one of those subsystems is represented by a clearly
documented *startup* and *shutdown* placeholder hook. Each future sprint
implements the body of its own hook (registering the engine/client into
``app.state``) without ever touching this orchestration layout.

Responsibilities
----------------
Startup (before ``yield``):
  * Log application startup with metadata.
  * Verify the centralized configuration is loadable.
  * Verify the Loguru logging system is initialized.
  * Run the registered startup hooks (PostgreSQL, Redis, AI models, STT,
    TTS, Telephony, Tool registry).

Shutdown (after ``yield`` / ``finally``):
  * Log graceful shutdown.
  * Run the registered cleanup hooks.
  * Drain Loguru's asynchronous sink queues via ``logger.complete()`` so no
    buffered record is lost when the process terminates.
  * Guarantee teardown runs even when the startup or the runtime raised.

The whole body is wrapped so the shutdown block always executes, including
when a startup hook fails or the server crashes mid-request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING, Any, Final

from fastapi import FastAPI
from loguru import logger

from backend.app.config.settings import AppEnvironment, Settings, get_settings
from backend.app.core.logger import configured_log_files, get_logger
from backend.app.database import get_engine, init_database

# Loguru types only exist in the type stub -> import for static analysis only.
if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any

#: Logger bound to this module.
_log: Logger = get_logger("lifespan")

# -- Hook signatures --------------------------------------------------------

type StartupHook = Callable[[FastAPI, Settings], Awaitable[None]]
type CleanupHook = Callable[[FastAPI, Settings], Awaitable[None]]

#: Supported by FastAPI's ``lifespan`` parameter.
type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


# -- Future service placeholder hooks ------------------------------------
# Startup and cleanup hooks are *real* orchestration points: each hook
# registers/tears down its subsystem into ``app.state``. Hooks of subsystems
# that are not implemented yet remain empty placeholders, edited only by
# their own future sprint, keeping the pair registered below untouched.


async def _startup_postgres(app: FastAPI, config: Settings) -> None:
    """Register the PostgreSQL engine into ``app.state`` (database sprint).

    Creates (or connects to) the schema through ``Base.metadata.create_all``
    and exposes the shared engine so other subsystems can build their own
    session factories. Outside ``PRODUCTION`` the app keeps serving with an
    in-memory fallback when the database is unavailable; in production a
    missing database is a hard startup failure.
    """
    try:
        engine = get_engine(config)
        await init_database(engine)
        app.state.database_engine = engine
    except Exception as exc:
        if config.environment is AppEnvironment.PRODUCTION:
            raise
        _log.warning(
            f"PostgreSQL unavailable ({exc}); continuing with in-memory state"
        )


async def _startup_redis(app: FastAPI, config: Settings) -> None:
    """Register the Redis client into ``app.state`` (cache sprint)."""


async def _startup_llm(app: FastAPI, config: Settings) -> None:
    """Register the selected LLM provider client (LLM sprint)."""


async def _startup_stt(app: FastAPI, config: Settings) -> None:
    """Register the speech-to-text client (STT sprint)."""


async def _startup_tts(app: FastAPI, config: Settings) -> None:
    """Register the text-to-speech client (TTS sprint)."""


async def _startup_telephony(app: FastAPI, config: Settings) -> None:
    """Register the telephony provider client (telephony sprint)."""


async def _startup_tools(app: FastAPI, config: Settings) -> None:
    """Register the tool registry (tools sprint)."""


async def _cleanup_postgres(app: FastAPI, config: Settings) -> None:
    """Dispose the PostgreSQL engine and pool (database sprint)."""
    engine = getattr(app.state, "database_engine", None)
    if engine is not None:
        await engine.dispose()


async def _cleanup_redis(app: FastAPI, config: Settings) -> None:
    """Close the Redis client connection (cache sprint)."""


async def _cleanup_llm(app: FastAPI, config: Settings) -> None:
    """Close the LLM client (LLM sprint)."""


async def _cleanup_stt(app: FastAPI, config: Settings) -> None:
    """Close the speech-to-text client (STT sprint)."""


async def _cleanup_tts(app: FastAPI, config: Settings) -> None:
    """Close the text-to-speech client (TTS sprint)."""


async def _cleanup_telephony(app: FastAPI, config: Settings) -> None:
    """Shut down the telephony provider client (telephony sprint)."""


async def _cleanup_tools(app: FastAPI, config: Settings) -> None:
    """Tear down the tool registry (tools sprint)."""


#: Startup hooks executed at application startup, in order.
_STARTUP_HOOKS: Final[tuple[tuple[str, StartupHook], ...]] = (
    ("postgres", _startup_postgres),
    ("redis", _startup_redis),
    ("llm", _startup_llm),
    ("stt", _startup_stt),
    ("tts", _startup_tts),
    ("telephony", _startup_telephony),
    ("tools", _startup_tools),
)

#: Cleanup placeholder hooks executed at application shutdown, in order.
_CLEANUP_HOOKS: Final[tuple[tuple[str, CleanupHook], ...]] = (
    ("postgres", _cleanup_postgres),
    ("redis", _cleanup_redis),
    ("llm", _cleanup_llm),
    ("stt", _cleanup_stt),
    ("tts", _cleanup_tts),
    ("telephony", _cleanup_telephony),
    ("tools", _cleanup_tools),
)


def create_lifespan() -> Lifespan:
    """Build the FastAPI lifespan for the whole application.

    Returns:
        An async context manager factory suitable for FastAPI's
        ``lifespan`` parameter: the returned context manager is entered at
        startup and left at shutdown (running ``yield`` once inside).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config: Settings = get_settings()
        log: Logger = _log.bind(app=config.app_name)

        log.info(
            f"Starting {config.app_name} v{config.app_version} "
            f"({config.environment.value})"
        )
        if config.log_file_enabled and not configured_log_files():
            raise RuntimeError(
                "Loguru is not initialized; the file sinks are missing. "
                "Call app.core.logger.setup_logging() before starting the app."
            )

        try:
            for name, hook in _STARTUP_HOOKS:
                log.debug(f"Running startup hook: {name}")
                await hook(app, config)
            yield
        finally:
            log.info("Shutting down the application")
            for name, hook in _CLEANUP_HOOKS:
                log.debug(f"Running cleanup hook: {name}")
                await hook(app, config)
            # Drain the enqueued sink queues so no buffered record is lost.
            await logger.complete()

    return lifespan


__all__ = ["create_lifespan"]
