"""Application entry point for the ASGI server.

This module is the single uvicorn target: it imports the application factory
and exposes the module-level ``app`` variable. No application setup happens
here — everything is composed inside :func:`create_app`.
"""

from backend.app.app import create_app

#: ASGI application served by uvicorn (``uvicorn backend.main:app``).
app = create_app()

__all__ = ["app"]
