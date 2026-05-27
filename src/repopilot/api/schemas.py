"""API schemas for future repair task endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RepairTaskRequest(BaseModel):
    """Request shape for a future issue-driven repair task."""

    issue_input: str = Field(min_length=1)
    repository_url: str | None = None
    dry_run: bool = True
    require_human_approval: bool = True


class RepairTaskResponse(BaseModel):
    """Response shape for a queued or dry-run repair task."""

    run_id: str
    status: str
    message: str
