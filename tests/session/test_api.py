"""End-to-end tests of the session REST endpoints.

The router is mounted directly on a throwaway FastAPI application (it is
not registered in the application factory) so the module stays
independently testable. The injected service comes from the ``client``
fixture, backed by a fresh in-memory repository per test.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from starlette.testclient import TestClient


class TestSessionApi:
    def test_start_creates_active_session(self, client: TestClient) -> None:
        response = client.post("/session/start")
        assert response.status_code == 201
        payload = response.json()
        assert payload["success"] is True
        assert payload["message"] == "Session started."
        data = payload["data"]
        assert UUID(data["session_id"]).version == 4
        assert data["status"] == "active"
        assert data["end_time"] is None
        assert data["start_time"]

    def test_end_ends_session(self, client: TestClient) -> None:
        started = client.post("/session/start").json()["data"]
        response = client.post("/session/end", json={"session_id": started["session_id"]})
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        data = payload["data"]
        assert data["session_id"] == started["session_id"]
        assert data["status"] == "ended"
        assert data["end_time"] is not None
        assert data["start_time"] == started["start_time"]

    def test_get_returns_session(self, client: TestClient) -> None:
        started = client.post("/session/start").json()["data"]
        response = client.get(f"/session/{started['session_id']}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["session_id"] == started["session_id"]
        assert data["status"] == "active"
        assert data["end_time"] is None

    def test_get_unknown_session_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/session/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["detail"]

    def test_get_invalid_session_id_returns_422(self, client: TestClient) -> None:
        response = client.get("/session/not-a-uuid")
        assert response.status_code == 422

    def test_end_unknown_session_returns_404(self, client: TestClient) -> None:
        response = client.post("/session/end", json={"session_id": str(uuid4())})
        assert response.status_code == 404

    def test_end_already_ended_session_returns_409(self, client: TestClient) -> None:
        started = client.post("/session/start").json()["data"]
        session_id = started["session_id"]
        assert client.post("/session/end", json={"session_id": session_id}).status_code == 200
        response = client.post("/session/end", json={"session_id": session_id})
        assert response.status_code == 409
        assert "already ended" in response.json()["detail"]

    def test_end_invalid_session_id_returns_422(self, client: TestClient) -> None:
        response = client.post("/session/end", json={"session_id": "not-a-uuid"})
        assert response.status_code == 422

    def test_end_missing_field_returns_422(self, client: TestClient) -> None:
        response = client.post("/session/end", json={})
        assert response.status_code == 422

    def test_end_extra_field_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/session/end", json={"session_id": str(uuid4()), "extra": True}
        )
        assert response.status_code == 422