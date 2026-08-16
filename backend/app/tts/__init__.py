"""Text-to-Speech integration layer.

A provider-independent text-to-speech abstraction with one concrete local
implementation:

* :class:`~backend.app.tts.ports.TtsPort` — the synthesis contract (text
  in, audio out); the application layer depends on it, never on a concrete
  provider.
* :class:`~backend.app.tts.ports.TtsResult` — the provider-independent
  synthesis result (audio bytes plus format, sample rate, channels and
  duration metadata).
* :class:`~backend.app.tts.service.TtsService` — validates text (empty /
  whitespace-only / too long) and delegates to the port.
* :class:`~backend.app.tts.pyttsx3.Pyttsx3Adapter` — the local, offline
  Windows SAPI5 engine (no API key, no internet, no model downloads).

Every adapter raises the clean errors defined in
:mod:`backend.app.tts.exceptions`; raw provider exceptions never escape
this package. The REST router is mounted by the application factory and
kept out of this package's public API.
"""

from backend.app.tts.exceptions import (
    TtsEmptyTextError,
    TtsError,
    TtsInvalidOutputError,
    TtsInvalidTextError,
    TtsProviderError,
    TtsTextTooLongError,
)
from backend.app.tts.ports import TtsPort, TtsResult
from backend.app.tts.pyttsx3 import Pyttsx3Adapter
from backend.app.tts.service import TtsService

__all__ = [
    "Pyttsx3Adapter",
    "TtsEmptyTextError",
    "TtsError",
    "TtsInvalidOutputError",
    "TtsInvalidTextError",
    "TtsPort",
    "TtsProviderError",
    "TtsResult",
    "TtsService",
    "TtsTextTooLongError",
]