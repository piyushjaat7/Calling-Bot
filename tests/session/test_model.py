"""Unit tests of the Session domain model.

Pure domain tests: no persistence, no framework, no HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from backend.app.session.exceptions import SessionStateError
from backend.app.session.model import Session, SessionStatus, utc_now


class TestSession:
    def test_creation_defaults(self) -> None:
        session = Session()
        assert isinstance(session.session_id, UUID)
        assert session.status is SessionStatus.ACTIVE
        assert session.is_active is True
        assert session.is_ended is False
        assert session.end_time is None
        assert isinstance(session.start_time, datetime)
        assert session.start_time.tzinfo is UTC

    def test_identity_unique_uuid4(self) -> None:
        ids = {Session().session_id for _ in range(100)}
        assert len(ids) == 100
        assert all(session_id.version == 4 for session_id in ids)

    def test_explicit_fields_accepted(self) -> None:
        session_id = uuid4()
        start_time = utc_now() - timedelta(minutes=5)
        session = Session(session_id=session_id, start_time=start_time)
        assert session.session_id == session_id
        assert session.start_time == start_time

    def test_status_vocabulary(self) -> None:
        assert {status.value for status in SessionStatus} == {"active", "ended"}

    def test_end_marks_ended(self) -> None:
        session = Session()
        ended_at = session.end()
        assert session.status is SessionStatus.ENDED
        assert session.is_ended is True
        assert session.is_active is False
        assert session.end_time == ended_at
        assert session.end_time is not None
        assert session.end_time.tzinfo is UTC
        assert session.end_time >= session.start_time

    def test_end_twice_raises_state_error(self) -> None:
        session = Session()
        session.end()
        with pytest.raises(SessionStateError) as excinfo:
            session.end()
        assert excinfo.value.session_id == session.session_id

    def test_active_session_cannot_have_end_time(self) -> None:
        with pytest.raises(ValueError, match="active session cannot have an end_time"):
            Session(status=SessionStatus.ACTIVE, end_time=utc_now())

    def test_ended_session_requires_end_time(self) -> None:
        with pytest.raises(ValueError, match="ended session must have an end_time"):
            Session(status=SessionStatus.ENDED, end_time=None)

    def test_end_time_before_start_rejected(self) -> None:
        start_time = utc_now()
        with pytest.raises(ValueError, match="must not precede"):
            Session(
                start_time=start_time,
                end_time=start_time - timedelta(minutes=1),
                status=SessionStatus.ENDED,
            )

    def test_naive_start_time_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            Session(start_time=utc_now().replace(tzinfo=None))

    def test_naive_end_time_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            Session(
                start_time=utc_now(),
                end_time=utc_now().replace(tzinfo=None),
                status=SessionStatus.ENDED,
            )

    def test_utc_now_returns_aware_utc(self) -> None:
        now = utc_now()
        assert now.tzinfo is UTC