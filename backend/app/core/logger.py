"""Centralized logging system built on Loguru.

This module is the single entry point for producing logs anywhere in the
application. No code outside of ``app/core`` should ever configure Loguru or
call ``print()``: modules obtain a logger from the helpers defined here.

What is configured
------------------
* Console logging on STDERR, colorized, respecting ``LOG_LEVEL``.
* Rotating file logging with automatic compression and retention for:
  ``application.log``, ``error.log`` and one dedicated file per category
  (``ai.log``, ``telephony.log``, ``conversation.log``, ``performance.log``).
* A stdlib ``logging`` interceptor so third party stacks (uvicorn, httpx,
  SQLAlchemy, ...) flow through the exact same pipeline.

Structured context
------------------
Records carry structured extra keys (``session_id``, ``request_id``,
``caller_id``, ``provider``, ``module``, plus ``trace_id`` and ``span_id``
which are reserved for the future OpenTelemetry exporter). Those keys are
always kept as structurable ``record["extra"]`` data for future metrics /
tracing exporters, and rendered inline into the human readable output.

Thread / async safety
---------------------
All sinks are enqueued (``enqueue=True``) so log writes never block or race
with the event loop. ``setup_logging`` is idempotent and guarded by a lock.

Future OpenTelemetry integration
--------------------------------
The formatting and interception points are centralized here; a future
``otel`` module only needs to (1) populate ``trace_id``/``span_id`` into
``extra`` and (2) attach an exporter at the sink level. No per-module
changes will be required.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from functools import wraps
from inspect import iscoroutinefunction
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any, Final, TypeVar, cast

from loguru import logger

from app.config.settings import PROJECT_ROOT, Settings, get_settings

# Loguru ships ``Logger``/``Record`` only in its type stub, so they are
# imported exclusively for static analysis and aliased for runtime safety.
if TYPE_CHECKING:
    from loguru import FilterFunction, FormatFunction, Logger, Record
else:
    Logger = Any
    Record = dict[str, Any]
    FilterFunction = Callable[[Record], bool]
    FormatFunction = Callable[[Record], str]

# ---------------------------------------------------------------------------
# Module level constants.
# ---------------------------------------------------------------------------

#: Timestamp format used by the shared record formatter (millisecond precision).
_TIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S.%f"

#: Ordered context keys rendered (when present) into every log line. The last
#: two are reserved for the future OpenTelemetry integration.
_CONTEXT_KEYS: Final[tuple[str, ...]] = (
    "session_id",
    "request_id",
    "caller_id",
    "provider",
    "module",
    "trace_id",
    "span_id",
)

#: Shared minimal level for the whole standard library logging tree.
_STDLIB_LOG_LEVEL: Final[int] = logging.DEBUG


class LogCategory(StrEnum):
    """Business categories used to split logs into dedicated files."""

    AI = "ai"
    TELEPHONY = "telephony"
    CONVERSATION = "conversation"
    PERFORMANCE = "performance"


@dataclass(frozen=True, slots=True)
class LogContext:
    """Immutable holder of the contextual keys attached to log records.

    Only the non-``None`` attributes are bound to the log record, so every
    record stays concise while callers keep a single, explicit object.

    Attributes:
        session_id: Identifier of the current conversation session.
        request_id: Correlation identifier of the current HTTP request.
        caller_id: Identifier of the external caller.
        provider: Active external provider (e.g. ``openai``, ``twilio``).
        module: Logical application module emitting the record.
        trace_id: Reserved for the future OpenTelemetry trace id.
        span_id: Reserved for the future OpenTelemetry span id.
    """

    session_id: str | None = None
    request_id: str | None = None
    caller_id: str | None = None
    provider: str | None = None
    module: str | None = None
    trace_id: str | None = None
    span_id: str | None = None

    def to_bindings(self) -> dict[str, str]:
        """Return only the set fields as Loguru ``bind()`` keyword arguments.

        Returns:
            A mapping of every non-``None`` context key to its value.
        """
        return {key: value for key, value in asdict(self).items() if value is not None}


# ---------------------------------------------------------------------------
# Module state.
# ---------------------------------------------------------------------------

#: Guards re-entrancy of :func:`setup_logging` across coroutines and threads.
_setup_lock: Final[threading.Lock] = threading.Lock()

#: ``True`` once the sinks have been configured for the current process.
_initialized: bool = False

#: Category name -> absolute path of the configured dedicated log files.
_log_files: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Formatter.
# ---------------------------------------------------------------------------


def _escape_template(value: str) -> str:
    """Escape values embedded into the Loguru format template.

    Arbitrary record data (module names, function names, context values) can
    contain ``{``/``}`` (which ``str.format_map`` would misread) or ``<``
    (which Loguru would treat as the start of a color tag such as
    ``<module>``). This neutralizes all three while the surrounding template
    tags stay intact. A bare ``>`` is harmless because tags need a ``<`` to
    begin.

    Args:
        value: The string to escape.

    Returns:
        The escaped string.
    """
    return value.replace("{", "{{").replace("}", "}}").replace("<", "\\<")


def _render_context(extra: Mapping[str, Any]) -> str:
    """Render the present structured context keys as a single string.

    Args:
        extra: The ``record["extra"]`` mapping of the log record.

    Returns:
        A string like `` session_id=123 module=stt``; empty when unused.
    """
    rendered: list[str] = []
    for key in _CONTEXT_KEYS:
        value: Any = extra.get(key)
        if value is not None:
            rendered.append(_escape_template(f"{key}={value}"))
    return f" {' '.join(rendered)}" if rendered else ""


def _format_record(record: Record) -> str:
    """Format a log record into its final human readable template.

    The returned template is interpreted by Loguru as a ``format_map``
    template (hence the ``{message}`` placeholder). Because it is dynamic,
    Loguru colorizes the ``<...>`` tags only when ``colorize=True`` (console)
    and strips them otherwise (files), so one formatter serves every sink.

    Args:
        record: The Loguru record to format.

    Returns:
        The rendered template that includes ``{message}`` and, when the
        record carries an exception, a trailing ``{exception}`` placeholder.
    """
    timestamp: str = record["time"].strftime(_TIME_FORMAT)[:-3]
    level_name: str = f"{record['level'].name:<8}"
    location: str = _escape_template(
        f"{record['name']}:{record['function']}:{record['line']}"
    )
    context: str = _render_context(record["extra"])

    # The trailing ``\n`` (like Loguru's default format) terminates the line
    # so line-buffered file sinks flush after every record.
    template: str = (
        f"<white>{timestamp}</white> | <level>{level_name}</level> | "
        f"<cyan>{location}</cyan>{context} | {{message}}\n"
    )
    if record["exception"]:
        template += "{exception}"
    return template


# ---------------------------------------------------------------------------
# Sink filters.
# ---------------------------------------------------------------------------


def _category_filter(category: LogCategory) -> Callable[[Record], bool]:
    """Build a Loguru filter that forwards records of ``category``.

    Args:
        category: The category the filter must match.

    Returns:
        A predicate accepting the matching records only.
    """

    def _filter(record: Record) -> bool:
        return record["extra"].get("category") == category.value

    return _filter


# ---------------------------------------------------------------------------
# Sink registration helpers.
# ---------------------------------------------------------------------------


def _resolve_log_directory(directory: str) -> Path:
    """Resolve ``directory`` against the project root when it is relative.

    Args:
        directory: The configured log directory (from ``LOG_DIR``).

    Returns:
        The absolute directory path, created if it does not exist yet.
    """
    path: Path = Path(directory)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _add_console_sink(config: Settings) -> None:
    """Register the colorized STDERR console sink.

    Args:
        config: The validated application settings.
    """
    logger.add(
        sys.stderr,
        format=_format_record,
        colorize=True,
        level=config.log_level.value,
        backtrace=config.log_backtrace,
        diagnose=config.log_diagnose,
        enqueue=config.log_enqueue,
    )


def _add_file_sinks(config: Settings) -> None:
    """Register the rotating, compressed, retained file sinks.

    Args:
        config: The validated application settings.
    """
    directory: Path = _resolve_log_directory(config.log_dir)
    common: dict[str, Any] = {
        "format": _format_record,
        "level": config.log_level.value,
        "rotation": config.log_rotation,
        "retention": config.log_retention,
        "compression": config.log_compression,
        "encoding": "utf-8",
        "enqueue": config.log_enqueue,
        "backtrace": config.log_backtrace,
        "diagnose": config.log_diagnose,
        "colorize": False,
    }

    # General event stream.
    logger.add(directory / "application.log", **common)
    _log_files["application"] = str(directory / "application.log")

    # Dedicated error stream (level only, no category filter).
    error_options: dict[str, Any] = {**common, "level": "ERROR"}
    logger.add(directory / "error.log", **error_options)
    _log_files["error"] = str(directory / "error.log")

    # Dedicated category streams.
    for category in LogCategory:
        path: Path = directory / f"{category.value}.log"
        logger.add(path, filter=_category_filter(category), **common)
        _log_files[category.value] = str(path)


# ---------------------------------------------------------------------------
# Standard-library logging interceptor.
# ---------------------------------------------------------------------------


class _LoguruInterceptHandler(logging.Handler):
    """Forward every stdlib ``logging`` record into Loguru.

    This guarantees that uvicorn, httpx, SQLAlchemy and the like produce
    their logs through the same pipeline (and, later, the same OTel
    exporters) as the application logs.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Redirect ``record`` to the Loguru logger.

        Args:
            record: The standard library log record to redirect.
        """
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the calling frame so the source location is reported correctly.
        frame: FrameType | None = logging.currentframe()
        depth: int = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def intercept_stdlib_logging() -> None:
    """Route the stdlib ``logging`` tree into Loguru.

    The interceptor is attached to the root logger only once. It can safely
    be called again (e.g. from a lifespan after uvicorn re-configures logging)
    to re-attach the handler.
    """
    root: logging.Logger = logging.getLogger()
    if any(isinstance(handler, _LoguruInterceptHandler) for handler in root.handlers):
        return
    root.addHandler(_LoguruInterceptHandler())
    root.setLevel(_STDLIB_LOG_LEVEL)


# ---------------------------------------------------------------------------
# Setup / reset.
# ---------------------------------------------------------------------------


def setup_logging(config: Settings | None = None) -> None:
    """Configure every Loguru sink for the process. Idempotent.

    Register the console and rotating file sinks described in the module
    docstring and intercept the stdlib ``logging`` tree. When a late
    framework replaces the root logger handlers (notably uvicorn), call
    :func:`intercept_stdlib_logging` again after it starts.

    Args:
        config: Override the global cached settings, mainly for tests.
            Defaults to :func:`get_settings`.

    Raises:
        RuntimeError: Propagated from Loguru when a sink cannot be added.
    """
    global _initialized

    if _initialized:
        return

    with _setup_lock:
        if _initialized:
            return

        config = config or get_settings()
        try:
            # Drop the default handler and any leftovers from a previous run.
            logger.remove()
            if config.log_console:
                _add_console_sink(config)
            if config.log_file_enabled:
                _add_file_sinks(config)
            intercept_stdlib_logging()
        except Exception:
            logger.remove()
            raise
        _initialized = True


def reset_logging() -> None:
    """Remove every sink and flag the logging system as unconfigured.

    Mainly intended for the test suite: each test case can call
    :func:`setup_logging` again with a dedicated configuration.
    """
    global _initialized

    with _setup_lock:
        _log_files.clear()
        _initialized = False
        logger.remove()


def configured_log_files() -> tuple[str, ...]:
    """Return the absolute paths of every configured file sink.

    Returns:
        A tuple of absolute log file paths (application first, then error,
        then categories), empty until :func:`setup_logging` runs.
    """
    return tuple(_log_files[key] for key in sorted(_log_files))


# ---------------------------------------------------------------------------
# Logger factories.
# ---------------------------------------------------------------------------


def get_logger(module: str) -> Logger:
    """Return a Loguru logger pre-bound with the given module context.

    Args:
        module: The emitting module name (e.g. ``stt``, ``conversation``).

    Returns:
        A Loguru logger bound with ``module``.
    """
    return logger.bind(module=module)


def get_category_logger(category: LogCategory, module: str = "") -> Logger:
    """Return a Loguru logger pre-bound to one business category.

    Records produced by this logger are written both to ``application.log``
    and to the dedicated ``<category>.log`` file.

    Args:
        category: The business category that routes the dedicated file.
        module: Optional module context to attach, e.g. ``telephony``.

    Returns:
        A Loguru logger bound to the category.
    """
    context: dict[str, str] = {"category": category.value}
    if module:
        context["module"] = module
    return logger.bind(**context)


def bind_context(log: Logger, context: LogContext) -> Logger:
    """Bind the structured context, if any, onto an existing logger.

    Args:
        log: The logger to enrich.
        context: The structured context to attach.

    Returns:
        A new logger carrying the non-``None`` context fields.
    """
    return log.bind(**context.to_bindings())


# ---------------------------------------------------------------------------
# Performance instrumentation.
# ---------------------------------------------------------------------------


def log_performance(
    operation: str, duration_ms: float, module: str = "", **context: Any
) -> None:
    """Log a measured operation into ``performance.log`` and application.

    Args:
        operation: The name of the measured operation (e.g. ``llm.generate``).
        duration_ms: The measured duration in milliseconds.
        module: The module context to attach.
        **context: Additional structured context (``session_id``, etc.).
    """
    bindings: dict[str, Any] = {
        key: value for key, value in context.items() if value is not None
    }
    if module:
        bindings["module"] = module
    logger.bind(category=LogCategory.PERFORMANCE.value, **bindings).info(
        f"{operation} completed in {duration_ms:.2f} ms"
    )


F = TypeVar("F", bound=Callable[..., Any])


def timed(module: str = "") -> Callable[[F], F]:
    """Decorate a callable (sync or async) to measure and log its duration.

    Example:
        >>> from app.core.logger import timed
        >>>
        >>> @timed(module="llm")
        ... async def generate(prompt): ...

    Args:
        module: The module context attached to the performance record.

    Returns:
        A decorator measuring and logging the wrapped callable duration.
    """

    def decorator(func: F) -> F:
        func_name: str = getattr(func, "__qualname__", repr(func))

        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start: float = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration: float = (time.perf_counter() - start) * 1000
                    log_performance(func_name, duration, module=module)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start: float = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration: float = (time.perf_counter() - start) * 1000
                log_performance(func_name, duration, module=module)

        return cast(F, wrapper)

    return decorator


__all__ = [
    "LogCategory",
    "LogContext",
    "bind_context",
    "configured_log_files",
    "get_category_logger",
    "get_logger",
    "intercept_stdlib_logging",
    "log_performance",
    "logger",
    "reset_logging",
    "setup_logging",
    "timed",
]
