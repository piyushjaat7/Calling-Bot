"""Fake implementations of the STT ports.

Duck-typed :class:`~backend.app.stt.ports.SttPort` implementation used
across the STT tests: no provider, no model, fully scripted.
"""

from __future__ import annotations

from backend.app.stt.ports import SttResult


class FakeSttPort:
    """SttPort returning a fixed result or raising a configured error."""

    def __init__(
        self,
        result: SttResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result: SttResult = result if result is not None else SttResult(text="")
        self.error: Exception | None = error
        self.calls: list[tuple[bytes, int]] = []

    async def transcribe(self, pcm: bytes, sample_rate: int) -> SttResult:
        """Record the call and return the result (or raise the error)."""
        self.calls.append((pcm, sample_rate))
        if self.error is not None:
            raise self.error
        return self.result