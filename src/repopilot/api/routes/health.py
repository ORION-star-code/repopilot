"""Health endpoint for API and deployment checks."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from repopilot import __version__
from repopilot.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    """Return stable health metadata without touching external systems."""
    settings = cast(Settings, request.app.state.settings)
    return {
        "name": settings.app_name,
        "version": __version__,
        "status": "ok",
        "environment": settings.environment,
    }
