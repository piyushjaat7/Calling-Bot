"""Health check REST endpoints.

Exposes the liveness endpoint used by load balancers, orchestrators and
monitoring probes. It is deliberately dependency-free: it never touches the
database, Redis or any provider so it keeps answering while the platform is
starting up or degrading gracefully.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

#: Router mounted by the application factory under ``/health``.
router = APIRouter(tags=["health"])


@router.get("/health", summary="Backend health status")
async def health() -> dict[str, Any]:
    """Return the backend liveness status.

    Returns:
        The documented success envelope with a status payload.
    """
    return {
        "success": True,
        "message": "Backend is healthy.",
        "data": {"status": "ok"},
    }


__all__ = ["router"]
