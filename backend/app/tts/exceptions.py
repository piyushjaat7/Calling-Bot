"""Clean, provider-independent error vocabulary of the TTS layer.

Every failure surfaced by a text-to-speech adapter or the TTS service is
raised as one of the :class:`TtsError` subclasses below; callers can catch
the whole hierarchy with a single ``except TtsError``. Raw provider
exceptions are always wrapped at the adapter boundary and never leak
through the application layer.

Input validation errors (empty / too long text) are distinguished from
provider failures so the REST layer can map each to its own HTTP status.
"""

from __future__ import annotations

__all__ = [
    "TtsEmptyTextError",
    "TtsError",
    "TtsInvalidOutputError",
    "TtsInvalidTextError",
    "TtsProviderError",
    "TtsTextTooLongError",
]


class TtsError(Exception):
    """Base class of every TTS layer error."""


class TtsInvalidTextError(TtsError):
    """Base class of input-validation failures (text is rejected)."""


class TtsEmptyTextError(TtsInvalidTextError):
    """Raised when the text is empty or whitespace-only."""


class TtsTextTooLongError(TtsInvalidTextError):
    """Raised when the text exceeds the configured length limit.

    Attributes:
        max_chars: The configured limit that was exceeded.
    """

    def __init__(self, max_chars: int) -> None:
        super().__init__(f"Text exceeds the length limit of {max_chars} characters.")
        self.max_chars: int = max_chars


class TtsProviderError(TtsError):
    """Raised when the TTS provider itself fails (engine, synthesis).

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail


class TtsInvalidOutputError(TtsError):
    """Raised when the provider returns unusable or empty audio.

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail