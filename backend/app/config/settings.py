"""Application configuration system.

This module is the single source of truth for all runtime configuration.

It uses :mod:`pydantic_settings` to load and validate configuration values
from two sources, in order of precedence:

1. Real environment variables (highest priority).
2. A ``.env`` file located at the project root (lowest priority).

Every value is strongly typed and validated the moment :class:`Settings` is
instantiated, so invalid configuration fails fast at startup instead of
failing silently somewhere deep inside a service.

Environment variables map directly to field names (case insensitive), e.g.
``DATABASE_URL`` -> ``database_url``, ``OPENAI_API_KEY`` -> ``openai_api_key``.
This flat, explicit naming keeps the mapping free of magic and matches the
keys documented in the repository ``.env.example`` file 1:1.

The module is deliberately provider-independent: LLM (OpenAI / Gemini /
Ollama), PostgreSQL, Redis and telephony providers are modelled as sibling
field groups on :class:`Settings`. Enabling or adding a new provider never
requires touching the rest of the application, it only requires configuring
it here and in the corresponding future module (``llm/``, ``stt/``, ``tts/``,
``telephony/``, ``database/``).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Final, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Project level constants.
# ---------------------------------------------------------------------------

#: Absolute path of the repository root (``backend/app/config`` -> repo root).
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]

#: The ``.env`` file read by pydantic-settings at instantiation time.
_ENV_FILE_PATH: Final[Path] = PROJECT_ROOT / ".env"

#: Human readable logging format shared by the console and file sinks.
_DEFAULT_LOG_FORMAT: Final[str] = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | {message}"
)

#: Network schemes accepted for any endpoint configuration.
_NETWORK_SCHEMES: Final[tuple[str, ...]] = ("http://", "https://")

__all__ = [
    "PROJECT_ROOT",
    "AppEnvironment",
    "LlmProvider",
    "LogLevel",
    "Settings",
    "TelephonyProvider",
    "get_settings",
    "settings",
]


# ---------------------------------------------------------------------------
# Enumerations used to expose strongly typed choice values.
# ---------------------------------------------------------------------------


class AppEnvironment(StrEnum):
    """Deployment environment of the running application."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Log levels understood by the Loguru sink configuration."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LlmProvider(StrEnum):
    """Supported large language model providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class TelephonyProvider(StrEnum):
    """Supported telephony providers (future expansion point)."""

    TWILIO = "twilio"
    VONAGE = "vonage"
    PLIVO = "plivo"


# ---------------------------------------------------------------------------
# Internal helpers shared by the validation rules.
# ---------------------------------------------------------------------------


def _is_secret_unset(secret: SecretStr | None) -> bool:
    """Return ``True`` when a secret is missing or an empty string.

    Args:
        secret: The secret to inspect.

    Returns:
        ``True`` when the secret cannot be used, ``False`` otherwise.
    """
    return secret is None or not secret.get_secret_value()


def _validate_url_scheme(value: str, allowed_schemes: set[str]) -> str:
    """Validate that a URL uses one of the allowed schemes.

    Args:
        value: The URL string to check.
        allowed_schemes: Schemes that are considered valid (lower case).

    Returns:
        The original URL when it is valid.

    Raises:
        ValueError: When the URL scheme is not in ``allowed_schemes``.
    """
    scheme: str = value.split("://", maxsplit=1)[0].lower()
    if scheme not in allowed_schemes:
        joined: str = ", ".join(sorted(allowed_schemes))
        raise ValueError(
            f"URL scheme '{scheme}' is not supported. Allowed schemes: {joined}."
        )
    return value


# ---------------------------------------------------------------------------
# Root settings object.
#
# Field naming convention: ``<GROUP>_<NAME>`` so that each environment
# variable maps to exactly one field, e.g. ``LOG_LEVEL`` -> ``log_level``.
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """The validated, cached, immutable configuration of the application.

    All values come from: environment variables -> ``.env`` -> defaults.
    The instance returned by :func:`get_settings` is a frozen singleton:
    once created it can never be mutated at runtime, which makes the
    configuration safe to share between any number of concurrent coroutines.
    """

    # -- Application metadata -------------------------------------------------
    app_name: str = Field(default="AI Communication Platform")  # ENV: APP_NAME
    app_version: str = Field(default="0.1.0")  # ENV: APP_VERSION
    environment: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT
    )  # ENV: ENVIRONMENT
    debug: bool = Field(default=False)  # ENV: DEBUG

    # -- Logging --------------------------------------------------------------
    # Consumed by the Loguru bootstrap in ``app/core/logger.py``.
    log_level: LogLevel = Field(default=LogLevel.INFO)  # ENV: LOG_LEVEL
    log_console: bool = Field(default=True)  # ENV: LOG_CONSOLE
    log_file_enabled: bool = Field(default=True)  # ENV: LOG_FILE_ENABLED
    log_dir: str = Field(default="logs")  # ENV: LOG_DIR
    log_rotation: str = Field(default="10 MB")  # ENV: LOG_ROTATION
    log_retention: str = Field(default="30 days")  # ENV: LOG_RETENTION
    log_compression: str = Field(default="zip")  # ENV: LOG_COMPRESSION
    log_format: str = Field(default=_DEFAULT_LOG_FORMAT)  # ENV: LOG_FORMAT
    log_enqueue: bool = Field(default=True)  # ENV: LOG_ENQUEUE
    log_backtrace: bool = Field(default=False)  # ENV: LOG_BACKTRACE
    log_diagnose: bool = Field(default=False)  # ENV: LOG_DIAGNOSE

    # -- PostgreSQL -----------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://calling_bot:calling_bot@localhost:5432/calling_bot"
    )  # ENV: DATABASE_URL
    database_pool_size: int = Field(default=10, ge=1, le=200)  # ENV: DATABASE_POOL_SIZE
    database_max_overflow: int = Field(
        default=20, ge=0, le=200
    )  # ENV: DATABASE_MAX_OVERFLOW
    database_pool_timeout: int = Field(default=30, gt=0)  # ENV: DATABASE_POOL_TIMEOUT
    database_pool_recycle: int = Field(default=1800, gt=0)  # ENV: DATABASE_POOL_RECYCLE
    database_echo: bool = Field(default=False)  # ENV: DATABASE_ECHO

    # -- Redis ----------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")  # ENV: REDIS_URL
    redis_db: int = Field(default=0, ge=0, le=15)  # ENV: REDIS_DB
    redis_decode_responses: bool = Field(default=True)  # ENV: REDIS_DECODE_RESPONSES

    # -- LLM provider selection ----------------------------------------------
    # When ``llm_default_provider`` is ``None`` the LLM layer is considered
    # unconfigured and no credential validation is enforced (foundation mode).
    # As soon as a provider is explicitly selected its credentials are
    # validated strictly. This keeps the foundation bootable without the
    # future AI modules while failing fast once configuration is attempted.
    llm_default_provider: LlmProvider | None = Field(
        default=None
    )  # ENV: LLM_DEFAULT_PROVIDER

    # -- OpenAI ---------------------------------------------------------------
    openai_api_key: SecretStr | None = Field(default=None)  # ENV: OPENAI_API_KEY
    openai_base_url: str | None = Field(default=None)  # ENV: OPENAI_BASE_URL
    openai_model: str = Field(default="gpt-4o-mini")  # ENV: OPENAI_MODEL
    openai_timeout_seconds: float = Field(
        default=60.0, gt=0.0
    )  # ENV: OPENAI_TIMEOUT_SECONDS

    # -- Gemini ---------------------------------------------------------------
    gemini_api_key: SecretStr | None = Field(default=None)  # ENV: GEMINI_API_KEY
    gemini_base_url: str | None = Field(default=None)  # ENV: GEMINI_BASE_URL
    gemini_model: str = Field(default="gemini-2.0-flash")  # ENV: GEMINI_MODEL
    gemini_timeout_seconds: float = Field(
        default=60.0, gt=0.0
    )  # ENV: GEMINI_TIMEOUT_SECONDS

    # -- Ollama ---------------------------------------------------------------
    # Ollama runs locally and therefore does not require an API key.
    ollama_base_url: str = Field(
        default="http://localhost:11434"
    )  # ENV: OLLAMA_BASE_URL
    ollama_model: str = Field(default="llama3.1")  # ENV: OLLAMA_MODEL
    ollama_timeout_seconds: float = Field(
        default=60.0, gt=0.0
    )  # ENV: OLLAMA_TIMEOUT_SECONDS

    # -- Telephony ------------------------------------------------------------
    # New providers (Vonage, Plivo, ...) are added as sibling field groups.
    telephony_provider: TelephonyProvider | None = Field(
        default=None
    )  # ENV: TELEPHONY_PROVIDER
    telephony_twilio_account_sid: str | None = Field(
        default=None
    )  # ENV: TELEPHONY_TWILIO_ACCOUNT_SID
    telephony_twilio_auth_token: SecretStr | None = Field(
        default=None
    )  # ENV: TELEPHONY_TWILIO_AUTH_TOKEN
    telephony_twilio_phone_number: str | None = Field(
        default=None
    )  # ENV: TELEPHONY_TWILIO_PHONE_NUMBER

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # -- Field validation -----------------------------------------------------

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        """Require a PostgreSQL dialect for the database URL."""
        allowed_schemes: set[str] = {
            "postgres",
            "postgresql",
            "postgresql+psycopg",
            "postgresql+asyncpg",
        }
        return _validate_url_scheme(value, allowed_schemes)

    @field_validator("redis_url")
    @classmethod
    def _validate_redis_url(cls, value: str) -> str:
        """Require a Redis dialect for the cache URL."""
        return _validate_url_scheme(value, {"redis", "rediss"})

    @field_validator("openai_base_url", "gemini_base_url", "ollama_base_url")
    @classmethod
    def _validate_provider_url(cls, value: str | None) -> str | None:
        """Require an HTTP(S) endpoint for any configured provider."""
        if value is not None and not value.startswith(_NETWORK_SCHEMES):
            raise ValueError(
                "Provider base URL must start with 'http://' or 'https://'."
            )
        return value

    # -- Cross-field validation ----------------------------------------------

    @model_validator(mode="after")
    def _validate_all(self) -> Self:
        """Run every cross-field validation rule in the right order."""
        self._validate_environment()
        self._validate_llm_provider()
        self._validate_telephony_provider()
        return self

    def _validate_environment(self) -> None:
        """Forbid enabling debug mode in production."""
        if self.environment is AppEnvironment.PRODUCTION and self.debug:
            raise ValueError("DEBUG=True is not allowed when ENVIRONMENT=production.")

    def _validate_llm_provider(self) -> None:
        """Require the credentials of the explicitly selected LLM provider."""
        if self.llm_default_provider is LlmProvider.OPENAI and _is_secret_unset(
            self.openai_api_key
        ):
            raise ValueError(
                "LLM_DEFAULT_PROVIDER=openai requires OPENAI_API_KEY to be set."
            )
        if self.llm_default_provider is LlmProvider.GEMINI and _is_secret_unset(
            self.gemini_api_key
        ):
            raise ValueError(
                "LLM_DEFAULT_PROVIDER=gemini requires GEMINI_API_KEY to be set."
            )

    def _validate_telephony_provider(self) -> None:
        """Require the credentials of the explicitly selected provider."""
        if self.telephony_provider is not TelephonyProvider.TWILIO:
            return
        missing: list[str] = []
        if not self.telephony_twilio_account_sid:
            missing.append("TELEPHONY_TWILIO_ACCOUNT_SID")
        if _is_secret_unset(self.telephony_twilio_auth_token):
            missing.append("TELEPHONY_TWILIO_AUTH_TOKEN")
        if not self.telephony_twilio_phone_number:
            missing.append("TELEPHONY_TWILIO_PHONE_NUMBER")
        if missing:
            raise ValueError(
                "TELEPHONY_PROVIDER=twilio requires the following variables: "
                + ", ".join(missing)
                + "."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application-wide singleton settings instance.

    The instance is created exactly once per process and then cached by
    :func:`functools.lru_cache`. Combined with ``frozen=True`` on the model,
    every import site receives the *same*, immutable :class:`Settings`
    object, which keeps the whole application consistent.

    Returns:
        The cached ``Settings`` instance.
    """
    return Settings()


#: Process-wide singleton instance. Import this directly for convenience;
#: use :func:`get_settings` when a lazy/cached creation point is preferred.
settings: Final[Settings] = get_settings()
