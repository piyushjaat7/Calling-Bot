"""LLM provider integration layer.

Provider adapters that implement the Conversation Core ``LlmPort`` contract.
Only Ollama ships today; OpenAI/Gemini plug in behind the same port without
touching the Conversation Engine.

Every adapter raises the clean errors defined in
:mod:`backend.app.llm.exceptions`; raw HTTP/client exceptions never escape
this package.
"""

from backend.app.llm.exceptions import (
    LlmConnectionError,
    LlmError,
    LlmHttpError,
    LlmInvalidResponseError,
    LlmTimeoutError,
)
from backend.app.llm.ollama import OllamaAdapter

__all__ = [
    "LlmConnectionError",
    "LlmError",
    "LlmHttpError",
    "LlmInvalidResponseError",
    "LlmTimeoutError",
    "OllamaAdapter",
]
