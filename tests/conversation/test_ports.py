"""Tests of the Conversation Engine ports.

The ports are provider-independent contracts; :class:`LlmResponse` is the
only concrete type in :mod:`backend.app.conversation.ports`. Protocol
conformance of the fake implementations is covered in ``test_engine.py``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from backend.app.conversation.ports import LlmResponse


class TestLlmResponse:
    def test_holds_content(self) -> None:
        response = LlmResponse(content="Hello there.")
        assert response.content == "Hello there."

    def test_is_immutable(self) -> None:
        response = LlmResponse(content="Hello there.")
        with pytest.raises(FrozenInstanceError):
            response.content = "other"  # type: ignore[misc]