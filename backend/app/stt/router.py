"""Speech-to-Text REST endpoints.

Exposes the STT service over HTTP:

* ``POST /stt/transcribe`` — upload a WAV file, receive its transcription.

The router only translates HTTP input/output and delegates to the service
(which validates the upload and delegates to the STT port); no business
logic lives here. The service is injected through a FastAPI dependency and
replaced by tests with ``app.dependency_overrides``.

The default service is wired through the real port: the local Vosk adapter
(model loaded lazily, so importing this module never requires a model to be
present).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.stt.exceptions import (
    SttAudioTooLargeError,
    SttEmptyAudioError,
    SttError,
    SttUnsupportedFormatError,
)
from backend.app.stt.ports import SttResult
from backend.app.stt.schemas import SttResponse, TranscriptionData
from backend.app.stt.service import SttService
from backend.app.stt.vosk import VoskAdapter

#: Shared default service: local Vosk engine (no API key, no internet).
_default_service: SttService = SttService(VoskAdapter())

#: Router carrying the speech-to-text endpoints.
router = APIRouter(prefix="/stt", tags=["speech-to-text"])


def get_stt_service() -> SttService:
    """FastAPI dependency providing the shared STT service."""
    return _default_service


@router.post(
    "/transcribe",
    response_model=SttResponse,
    summary="Transcribe an uploaded WAV audio file",
)
async def transcribe_audio(
    file: Annotated[UploadFile, File(description="16-bit mono PCM WAV file")],
    service: Annotated[SttService, Depends(get_stt_service)],
) -> SttResponse:
    """Transcribe an uploaded WAV audio file.

    Args:
        file: The uploaded WAV audio (multipart form field ``file``).
        service: The injected STT service.

    Returns:
        The success envelope carrying the transcription.

    Raises:
        HTTPException: ``422`` when the audio is empty, ``413`` when it
            exceeds the size limit, ``415`` when it is not a supported
            WAV/PCM file, ``502`` when the STT provider fails or returns
            an unusable response.
    """
    audio: bytes = await file.read()
    try:
        result: SttResult = await service.transcribe(audio)
    except SttEmptyAudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SttAudioTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except SttUnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except SttError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SttResponse(
        success=True,
        message="Transcription completed.",
        data=TranscriptionData.from_result(result),
    )


__all__ = ["get_stt_service", "router"]