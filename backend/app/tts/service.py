"""TTS application service — the input-validation boundary.

The service owns everything that is *not* provider-specific: it validates
the text input (emptiness, length) and delegates the actual synthesis to
the injected :class:`~backend.app.tts.ports.TtsPort`. Application and REST
code depend on this class (and through it on the port abstraction) — never
on a concrete provider.
"""

from __future__ import annotations

from backend.app.config.settings import Settings, get_settings
from backend.app.tts.exceptions import (
    TtsEmptyTextError,
    TtsTextTooLongError,
)
from backend.app.tts.ports import TtsPort, TtsResult


class TtsService:
    """Validates text input and synthesizes it through the TTS port.

    Args:
        port: The text-to-speech port (provider abstraction).
        max_text_chars: Optional text length limit; defaults to
            ``TTS_MAX_TEXT_CHARS``.
    """

    def __init__(
        self,
        port: TtsPort,
        max_text_chars: int | None = None,
    ) -> None:
        config: Settings = get_settings()
        self._port: TtsPort = port
        self._max_text_chars: int = (
            max_text_chars or config.tts_max_text_chars
        )

    async def synthesize(self, text: str) -> TtsResult:
        """Validate text and synthesize speech for it.

        Args:
            text: The text to speak.

        Returns:
            The provider-independent synthesis result.

        Raises:
            TtsEmptyTextError: When the text is empty or whitespace-only.
            TtsTextTooLongError: When the text exceeds the length limit.
            TtsProviderError: Propagated from the port when the provider
                fails.
            TtsInvalidOutputError: Propagated from the port when the
                provider returns unusable audio.
        """
        self._validate_text(text)
        return await self._port.synthesize(text)

    def _validate_text(self, text: str) -> None:
        """Enforce the input contract.

        Args:
            text: The text to validate.

        Raises:
            TtsEmptyTextError: When the text is empty or whitespace-only.
            TtsTextTooLongError: When the text exceeds the length limit.
        """
        if not text.strip():
            raise TtsEmptyTextError("Text is empty.")
        if len(text) > self._max_text_chars:
            raise TtsTextTooLongError(self._max_text_chars)


__all__ = ["TtsService"]