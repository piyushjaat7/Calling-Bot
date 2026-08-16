"""STT request/response schemas.

Strict, validated Pydantic models exposing the STT result to the HTTP
layer. Responses serialize only the documented envelope and never leak
provider internals.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.stt.ports import SttResult


class TranscriptionData(BaseModel):
    """Serialized view of a transcription result.

    Attributes:
        text: The transcribed text (``""`` for silence).
    """

    model_config = ConfigDict(strict=True, extra="forbid", from_attributes=True)

    text: str

    @classmethod
    def from_result(cls, result: SttResult) -> TranscriptionData:
        """Build the serialized view from a domain result.

        Args:
            result: The domain transcription result to serialize.

        Returns:
            The validated data view of the result.
        """
        return cls.model_validate(result)


class SttResponse(BaseModel):
    """Success envelope returned by every STT endpoint."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    message: str
    data: TranscriptionData


__all__ = ["SttResponse", "TranscriptionData"]