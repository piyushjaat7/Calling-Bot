"""Speech-to-Text integration layer.

A provider-independent speech-to-text abstraction with one concrete local
implementation:

* :class:`~backend.app.stt.ports.SttPort` — the transcription contract
  (validated PCM audio in, text out); the application layer depends on it,
  never on a concrete provider.
* :class:`~backend.app.stt.ports.SttResult` — the provider-independent
  transcription result.
* :class:`~backend.app.stt.service.SttService` — validates uploads
  (empty / oversized / unsupported format) and delegates to the port.
* :class:`~backend.app.stt.vosk.VoskAdapter` — the local, offline,
  CPU-only Vosk engine (no API key, no internet, no GPU).

Every adapter raises the clean errors defined in
:mod:`backend.app.stt.exceptions`; raw provider exceptions never escape
this package. The REST router is mounted by the application factory and
kept out of this package's public API.
"""

from backend.app.stt.exceptions import (
    SttAudioTooLargeError,
    SttEmptyAudioError,
    SttError,
    SttInvalidAudioError,
    SttInvalidResponseError,
    SttProviderError,
    SttUnsupportedFormatError,
)
from backend.app.stt.ports import SttPort, SttResult
from backend.app.stt.service import SttService
from backend.app.stt.vosk import VoskAdapter

__all__ = [
    "SttAudioTooLargeError",
    "SttEmptyAudioError",
    "SttError",
    "SttInvalidAudioError",
    "SttInvalidResponseError",
    "SttPort",
    "SttProviderError",
    "SttResult",
    "SttService",
    "SttUnsupportedFormatError",
    "VoskAdapter",
]