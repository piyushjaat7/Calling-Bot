"""FastAPI application factory — the composition root of the backend.

This module is the *single* place where a :class:`~fastapi.FastAPI` instance
is created. Every cross-cutting concern is wired in a fixed, dependency-safe
order so that a running application is complete and its components are easy
to reason about:

``create_app()``
    Load validated settings (:mod:`backend.app.config.settings`)
        -> bootstrap logging (:mod:`backend.app.core.logger`)
        -> build the ``FastAPI`` instance (OpenAPI / Swagger UI / ReDoc)
        -> attach the lifespan (:mod:`backend.app.core.lifespan`)
        -> register middleware
        -> register exception handlers
        -> register API routers
        -> return the ready application

The handlers, middlewares and routers are each registered by a small,
single-responsibility private helper. Future modules (AI, WebSocket,
telephony, memory, dashboard, logging endpoints) plug in by *appending*
their router / middleware / hook to the relevant helper — the wiring here
doubles as a living inventory of the backend and never requires
restructuring ``create_app`` itself.

Design goals
------------
* **Composition root only.** No other module may instantiate FastAPI.
* **Extension points, not implementations.** Authentication, database,
  Redis, AI, memory, STT/TTS, WebSockets and telephony are deliberately
  absent; they arrive as routers, hooks and middleware appended below.
* **Failing fast.** Settings are loaded and logging is bootstrapped before
  the instance is created, so configuration/logging errors surface at startup
  instead of at the first request.
* **Testable.** ``create_app(config=...)`` accepts an injected configuration
  for the test suite while defaulting to the global cached singleton.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Final, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.config.settings import AppEnvironment, Settings, get_settings
from backend.app.conversation.router import router as conversation_router
from backend.app.core.lifespan import create_lifespan
from backend.app.core.logger import get_logger, setup_logging
from backend.app.session.router import router as session_router
from backend.app.stt.router import router as stt_router
from backend.app.tts.router import router as tts_router

# Loguru only exposes the ``Logger`` type in its type stub, hence the
# TYPE_CHECKING import with a runtime alias.
if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = Any

#: Human readable description surfaced on the OpenAPI / Swagger / ReDoc docs.
_API_DESCRIPTION: Final[str] = (
    "REST and WebSocket backend of the AI Communication Platform. "
    "This OpenAPI contract is the single interface for the dashboard, the "
    "real-time clients and the inbound telephony webhooks."
)

#: Status code of the generic unhandled-error response.
_INTERNAL_ERROR_STATUS: Final[int] = 500

#: Callable shape accepted by FastAPI/Starlette ``add_exception_handler``.
type ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]

#: Logger bound to this module.
_log: Logger = get_logger("app")


def create_app(config: Settings | None = None) -> FastAPI:
    """Create and wire the root FastAPI application.

    Args:
        config: Optional validated settings (mainly for the test suite).
            Defaults to the global cached singleton via :func:`get_settings`.

    Returns:
        A ready-to-serve ``FastAPI`` instance with lifespan, middleware,
        exception handlers and routes registered.

    Raises:
        RuntimeError: Propagated when the configured settings are invalid
            or the logging system cannot be bootstrapped.
    """
    settings: Settings = config if config is not None else get_settings()
    setup_logging(settings)

    _log_application_metadata(settings)

    app: FastAPI = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=_API_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        # FastAPI reads the metadata from our ``lifespan`` parameter; the
        # context manager returned by ``create_lifespan()`` is entered on
        # server startup and left on shutdown.
        lifespan=create_lifespan(),
        debug=settings.debug,
    )

    _register_middlewares(app, settings)
    _register_exception_handlers(app)
    _register_routes(app)

    _log.info("FastAPI application built")
    return app


def _log_application_metadata(settings: Settings) -> None:
    """Log the application identity at startup.

    Args:
        settings: The active application configuration.
    """
    _log.info(f"Application: {settings.app_name}")
    _log.info(f"Version: {settings.app_version}")
    _log.info(f"Environment: {settings.environment.value.capitalize()}")


def _register_middlewares(app: FastAPI, config: Settings) -> None:
    """Attach the global request middleware stack.

    Middlewares run in registration order around every request. CORS is the
    only one provisioned for now; future work appends, in order, request id
    propagation, access logging, rate limiting, request body validation and
    authentication — each as its own ``app.add_middleware(...)`` line.

    Args:
        app: The application to attach the middleware to.
        config: The validated settings used to gate middleware behaviour.
    """
    # Cross-Origin Resource Sharing for the dashboard and real-time clients.
    # Development allows any origin; production expects an explicit allow
    # list (provisioned via environment configuration) and stays closed by
    # default (an empty list disables the CORS middleware entirely).
    if config.environment is AppEnvironment.PRODUCTION:
        allow_origins: list[str] = []
        allow_credentials: bool = True
    else:
        allow_origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_exception_handlers(app: FastAPI) -> None:
    """Register the HTTP interface of the error pipeline.

    Every response produced here follows the documented error envelope:
    ``{"success": false, "message": "...", "error": {...}}``. Handlers
    receive the request so the message can be bound to its queue before
    being answered — and the two internal ones never leak stack traces.

    Args:
        app: The application to register the handlers on.
    """
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, _handle_validation_error)
    )
    app.add_exception_handler(HTTPException, cast(ExceptionHandler, _handle_http_error))
    app.add_exception_handler(
        Exception, cast(ExceptionHandler, _handle_unhandled_error)
    )


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a 422 envelope for invalid request payloads.

    Args:
        request: The failing HTTP request (used for future tracing).
        exc: The validation exception raised by FastAPI.

    Returns:
        A structured ``422`` error response.
    """
    _log.warning(f"Request validation failed for {request.url.path}")
    payload: dict[str, Any] = _error_payload(
        "Request validation failed.",
        {"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=payload)


async def _handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    """Return an envelope for application-level HTTP errors.

    Args:
        request: The framework request (used in future tracing).
        exc: The ``HTTPException`` supersed by FastAPI.

    Returns:
        A structured error response using the exception status code.
    """
    return JSONResponse(status_code=exc.status_code, content=_error_payload(exc.detail))


async def _handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Degrade to a safe 500 envelope for any unhandled exception.

    Args:
        request: The framework request that triggered the error.
        exc: The unexpected exception (only logged, never returned).

    Returns:
        A structured generic ``500`` error response.
    """
    _log.exception(
        f"Unhandled exception while serving {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=_INTERNAL_ERROR_STATUS,
        content=_error_payload("Internal server error."),
    )


def _error_payload(message: str, error: Any | None = None) -> dict[str, Any]:
    """Build the documented error envelope.

    Args:
        message: Human readable error description.
        error: Optional structured error details.

    Returns:
        The canonical ``{"success": false, "message", "error"}`` payload.
    """
    return {
        "success": False,
        "message": message,
        "error": error if error is not None else {},
    }


def _register_routes(app: FastAPI) -> None:
    """Register every REST API router of the application.

    Health, session, conversation, speech-to-text and text-to-speech
    routers are mounted here; future modules (messages, memory, tools,
    settings, logs) each ship an ``APIRouter`` instance and are appended
    in declaration order to become reachable under the HTTP interface
    immediately. The real-time WebSocket endpoints are registered the same
    way.

    Args:
        app: The application to attach the routers to.
    """
    app.include_router(health_router)
    app.include_router(session_router)
    app.include_router(conversation_router)
    app.include_router(stt_router)
    app.include_router(tts_router)


#: Public entry point of the module.
__all__ = ["create_app"]
