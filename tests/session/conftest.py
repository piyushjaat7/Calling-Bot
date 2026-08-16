"""Shared fixtures of the Session test suite.

Providers a fresh in-memory repository and service per test, plus a
``TestClient`` that mounts the session router directly (it is not part of
the application factory) with the injected service.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.app.session.repository import SessionInMemoryRepository
from backend.app.session.router import get_session_service, router
from backend.app.session.service import SessionService


@pytest.fixture
def session_repository() -> SessionInMemoryRepository:
    """A fresh in-memory repository per test."""
    return SessionInMemoryRepository()


@pytest.fixture
def session_service(session_repository: SessionInMemoryRepository) -> SessionService:
    """A session service bound to the fresh repository."""
    return SessionService(session_repository)


@pytest.fixture
def client(session_service: SessionService) -> Iterator[TestClient]:
    """A TestClient mounting the session router with the injected service."""

    app = FastAPI()
    app.dependency_overrides[get_session_service] = lambda: session_service
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client