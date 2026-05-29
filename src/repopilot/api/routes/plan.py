"""Plan endpoint for creating repair plans."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from repopilot.config import get_settings
from repopilot.issue_intake import normalize_issue_input
from repopilot.repair_workflow import create_repair_plan
from repopilot.repo_analysis import inspect_repository
from repopilot.tools.safety import contain_path

router = APIRouter(tags=["plan"])


class PlanRequest(BaseModel):
    """Request body for the plan endpoint."""

    input: str = Field(min_length=1, description="GitHub Issue URL or raw bug description.")
    repo: str = Field(default=".", description="Repository path to inspect.")


class PlanResponse(BaseModel):
    """Response body for the plan endpoint."""

    summary: str
    target_files: list[str]
    steps: list[str]
    verification: list[str]


@router.post("/plan", response_model=PlanResponse)
def plan(request: PlanRequest) -> PlanResponse:
    """Create a starter repair plan from input and repository context."""
    settings = get_settings()
    root = Path(settings.workspace_root)
    try:
        validated = contain_path(request.repo, root)
        repair_request = normalize_issue_input(request.input)
        snapshot = inspect_repository(validated)
        result = create_repair_plan(repair_request, snapshot)
        return PlanResponse(**asdict(result))
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
