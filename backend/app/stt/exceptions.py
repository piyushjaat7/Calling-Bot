"""Clean, provider-independent error vocabulary of the STT layer.

Every failure surfaced by a speech-to-text adapter or the STT service is
raised as one of the :class:`SttError` subclasses below; callers can catch
the whole hierarchy with a single ``except SttError``. Raw provider
exceptions are always wrapped at the adapter boundary and never leak
through the application layer.

Input validation errors (empty / too large / unsupported audio) are
distinguished from provider failures so the REST layer can map each to its
own HTTP status.
"""

from __future__ import annotations

__all__ = [
    "SttAudioTooLargeError",
    "SttEmptyAudioError",
    "SttError",
    "SttInvalidAudioError",
    "SttInvalidResponseError",
    "SttProviderError",
    "SttUnsupportedFormatError",
]


class SttError(Exception):
    """Base class of every STT layer error."""


class SttInvalidAudioError(SttError):
    """Base class of input-validation failures (audio is rejected)."""


class SttEmptyAudioError(SttInvalidAudioError):
    """Raised when the audio payload carries no bytes at all."""


class SttAudioTooLargeError(SttInvalidAudioError):
    """Raised when the audio payload exceeds the configured size limit.

    Attributes:
        max_bytes: The configured limit that was exceeded.
    """

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"Audio exceeds the size limit of {max_bytes} bytes.")
        self.max_bytes: int = max_bytes


class SttUnsupportedFormatError(SttInvalidAudioError):
    """Raised when the audio is not a supported WAV/PCM payload.

    Attributes:
        detail: Human readable description of the format problem.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail


class SttProviderError(SttError):
    """Raised when the STT provider itself fails (model, recognizer).

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail


class SttInvalidResponseError(SttError):
    """Raised when the provider returns an unusable or empty response.

    Attributes:
        detail: Human readable description of the failure.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail: str = detail