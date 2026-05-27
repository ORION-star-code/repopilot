"""ASGI entrypoint for `uvicorn repopilot.main:app`."""

from __future__ import annotations

from .api import create_app

app = create_app()
