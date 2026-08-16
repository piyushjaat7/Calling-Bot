"""Text-to-Speech REST endpoints.

Exposes the TTS service over HTTP:

* ``POST /tts/synthesize`` — send text, receive a base64-encoded WAV
  synthesis plus its audio metadata.

The router only translates HTTP input/output and delegates to the service
(which validates the text and delegates to the TTS port); no business
logic lives here. The service is injected through a FastAPI dependency and
replaced by tests with ``app.dependency_overrides``.

The default service is wired through the real port: the local Pyttsx3
adapter (engine initialized lazily, so importing this module never
requires a working speech engine).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.tts.exceptions import (
    TtsError,
    TtsInvalidTextError,
)
from backend.app.tts.ports import TtsResult
from backend.app.tts.pyttsx3 import Pyttsx3Adapter
from backend.app.tts.schemas import SynthesisData, SynthesizeRequest, TtsResponse
from backend.app.tts.service import TtsService

#: Shared default service: local SAPI5 engine (no API key, no internet).
_default_service: TtsService = TtsService(Pyttsx3Adapter())

#: Router carrying the text-to-speech endpoints.
router = APIRouter(prefix="/tts", tags=["text-to-speech"])


def get_tts_service() -> TtsService:
    """FastAPI dependency providing the shared TTS service."""
    return _default_service


@router.post(
    "/synthesize",
    response_model=TtsResponse,
    summary="Synthesize speech from text",
)
async def synthesize_speech(
    payload: SynthesizeRequest,
    service: Annotated[TtsService, Depends(get_tts_service)],
) -> TtsResponse:
    """Synthesize speech for the given text.

    Args:
        payload: The request body carrying the text to speak.
        service: The injected TTS service.

    Returns:
        The success envelope carrying the WAV audio (base64) and its
        metadata.

    Raises:
        HTTPException: ``422`` when the text is empty, whitespace-only or
            too long, ``502`` when the TTS provider fails or returns
            unusable audio.
    """
    try:
        result: TtsResult = await service.synthesize(payload.text)
    except TtsInvalidTextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TtsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TtsResponse(
        success=True,
        message="Speech synthesized.",
        data=SynthesisData.from_result(result),
    )


__all__ = ["get_tts_service", "router"]