"""Fake implementations of the TTS ports and engine.

Duck-typed :class:`~backend.app.tts.ports.TtsPort` implementation and a
fake ``pyttsx3`` engine used across the TTS tests: no provider, no
synthesis, fully scripted. The fake engine records ``save_to_file`` paths
and writes a scripted payload when ``runAndWait`` is called.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.tts.ports import TtsResult
from tests.stt.wav_builder import make_wav


class FakeTtsPort:
    """TtsPort returning a fixed result or raising a configured error."""

    def __init__(
        self,
        result: TtsResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result: TtsResult = result if result is not None else self._default_result()
        self.error: Exception | None = error
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> TtsResult:
        """Record the call and return the result (or raise the error)."""
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.result

    @staticmethod
    def _default_result() -> TtsResult:
        """A 0.1 s silence synthesis at 16 kHz mono 16-bit."""
        audio: bytes = make_wav()
        return TtsResult(
            audio=audio,
            sample_rate=16000,
            channels=1,
            bits_per_sample=16,
            duration_seconds=0.1,
        )


class FakePyttsx3Engine:
    """Duck-typed SAPI5 engine writing a scripted payload to a WAV file.

    Args:
        payload: The bytes written to the ``save_to_file`` target when
            ``runAndWait`` runs; ``None`` simulates an engine that never
            writes a file (the empty ``mkstemp`` file stays empty).
        save_error: Optional exception raised by ``save_to_file``.
        remove_target: When ``True``, ``runAndWait`` deletes the target
            file — simulating an engine that never creates it (the
            ``mkstemp`` placeholder is removed first).
    """

    def __init__(
        self,
        payload: bytes | None = None,
        save_error: Exception | None = None,
        remove_target: bool = False,
    ) -> None:
        self.payload: bytes | None = payload
        self.save_error: Exception | None = save_error
        self.remove_target: bool = remove_target
        self.saved_paths: list[str] = []
        self.voice: str | None = None
        self.ran: bool = False

    def save_to_file(self, text: str, path: str) -> None:
        """Record the target path (or raise the configured error)."""
        self.saved_paths.append(path)
        if self.save_error is not None:
            raise self.save_error

    def runAndWait(self) -> None:
        """Simulate synthesis by writing the payload to the last path."""
        self.ran = True
        if not self.saved_paths:
            return
        target = Path(self.saved_paths[-1])
        if self.remove_target:
            target.unlink(missing_ok=True)
        elif self.payload is not None:
            target.write_bytes(self.payload)

    def setProperty(self, name: str, value: str) -> None:
        """Record the applied voice property."""
        if name == "voice":
            self.voice = value

    def stop(self) -> None:
        """No-op kept for engine-lifecycle compatibility."""


__all__ = ["FakePyttsx3Engine", "FakeTtsPort"]