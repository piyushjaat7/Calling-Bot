"""Shared fixtures of the STT test suite.

Provides a fake-backed STT service and a ``TestClient`` mounting the STT
router directly with the injected service, mirroring the session test
suite conventions.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.app.stt.router import get_stt_service, router
from backend.app.stt.service import SttService
from tests.stt.fakes import FakeSttPort


@pytest.fixture
def stt_service() -> SttService:
    """A fake-backed STT service (no provider, no model)."""
    return SttService(FakeSttPort())


@pytest.fixture
def client(stt_service: SttService) -> Iterator[TestClient]:
    """A TestClient mounting the STT router with the injected service."""
    with make_client(stt_service) as test_client:
        yield test_client


def make_client(service: SttService) -> TestClient:
    """Build a TestClient around the STT router with the given service."""
    app = FastAPI()
    app.dependency_overrides[get_stt_service] = lambda: service
    app.include_router(router)
    return TestClient(app)