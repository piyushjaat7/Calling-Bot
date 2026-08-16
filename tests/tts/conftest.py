"""Shared fixtures of the TTS test suite.

Provides a fake-backed TTS service and a ``TestClient`` mounting the TTS
router directly with the injected service, mirroring the STT test suite
conventions.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.app.tts.router import get_tts_service, router
from backend.app.tts.service import TtsService
from tests.tts.fakes import FakeTtsPort


@pytest.fixture
def tts_service() -> TtsService:
    """A fake-backed TTS service (no provider, no engine)."""
    return TtsService(FakeTtsPort())


@pytest.fixture
def client(tts_service: TtsService) -> Iterator[TestClient]:
    """A TestClient mounting the TTS router with the injected service."""
    with make_client(tts_service) as test_client:
        yield test_client


def make_client(service: TtsService) -> TestClient:
    """Build a TestClient around the TTS router with the given service."""
    app = FastAPI()
    app.dependency_overrides[get_tts_service] = lambda: service
    app.include_router(router)
    return TestClient(app)


__all__ = ["make_client"]