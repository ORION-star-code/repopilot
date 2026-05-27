"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from repopilot import __version__
from repopilot.config import Settings, get_settings

from .routes import health


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a RepoPilot API app with explicit settings."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        description="Production-oriented AI code repair agent API skeleton.",
    )
    app.state.settings = resolved_settings
    app.include_router(health.router)
    return app
