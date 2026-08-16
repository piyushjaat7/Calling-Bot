"""Clean, provider-independent error vocabulary of the LLM layer.

Every failure surfaced by an adapter is raised as one of the
:class:`LlmError` subclasses below; callers can catch the whole hierarchy
with a single ``except LlmError``. Raw HTTP/client exceptions are always
wrapped at the adapter boundary and never leak through the Conversation
layer.
"""

from __future__ import annotations

__all__ = [
    "LlmConnectionError",
    "LlmError",
    "LlmHttpError",
    "LlmInvalidResponseError",
    "LlmTimeoutError",
]


class LlmError(Exception):
    """Base class of every LLM layer error."""


class LlmConnectionError(LlmError):
    """Raised when the provider endpoint cannot be reached.

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail


class LlmTimeoutError(LlmError):
    """Raised when a provider call exceeds the configured timeout.

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail


class LlmHttpError(LlmError):
    """Raised when the provider responds with a non-success status.

    Attributes:
        status_code: The HTTP status returned by the provider.
        detail: Sanitized, provider-provided error description.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"LLM provider returned HTTP {status_code}: {detail}")
        self.status_code: int = status_code
        self.detail: str = detail


class LlmInvalidResponseError(LlmError):
    """Raised when the provider returns an unusable or empty response.

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail
