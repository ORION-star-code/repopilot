"""Repair endpoints for dry-run and full workflow execution."""

from __future__ import annotations

import shlex
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from repopilot.issue_fetchers import FixtureIssueFetcher
from repopilot.issue_intake import normalize_issue_input
from repopilot.repair_workflow import run_dry_repair_workflow
from repopilot.repo_analysis import inspect_repository
from repopilot.workflows.orchestrator import RealRepairWorkflowOrchestrator

router = APIRouter(tags=["repair"])


class DryRunRequest(BaseModel):
    """Request body for the dry-run endpoint."""

    input: str = Field(min_length=1, description="GitHub Issue URL or raw bug description.")
    repo: str = Field(default=".", description="Repository path.")
    fixture: str | None = Field(default=None, description="Path to local JSON fixture file.")


class DryRunResponse(BaseModel):
    """Response body for the dry-run endpoint."""

    workflow_status: str
    retry_count: int
    max_retries: int
    approval_required: bool
    plan: dict[str, Any]
    artifacts: dict[str, Any]


@router.post("/dry-run", response_model=DryRunResponse)
def dry_run(request: DryRunRequest) -> DryRunResponse:
    """Run the no-side-effect repair workflow and emit planned artifacts."""
    try:
        fetcher = FixtureIssueFetcher(request.fixture) if request.fixture else None
        repair_request = normalize_issue_input(request.input, issue_fetcher=fetcher)
        snapshot = inspect_repository(Path(request.repo))
        result = run_dry_repair_workflow(repair_request, snapshot)
        return DryRunResponse(
            workflow_status=result.workflow_status,
            retry_count=result.retry_count,
            max_retries=result.max_retries,
            approval_required=result.approval_required,
            plan=asdict(result.plan),
            artifacts=asdict(result.artifacts),
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class RunRequest(BaseModel):
    """Request body for the full run endpoint."""

    input: str = Field(min_length=1, description="GitHub Issue URL or raw bug description.")
    repo: str = Field(default=".", description="Repository path to repair.")
    diff: str = Field(default="", description="Unified diff to apply.")
    test_cmd: str = Field(default="python -m pytest -q", description="Validation command.")
    max_retries: int = Field(default=2, ge=0, le=10, description="Max retry attempts.")
    fixture: str | None = Field(default=None, description="Path to local JSON fixture file.")


class RunResponse(BaseModel):
    """Response body for the full run endpoint."""

    stage: str
    status: str
    retry_count: int
    max_retries: int
    history: list[str]
    plan: dict[str, Any] | None
    artifacts: dict[str, Any]
    search_results: list[dict[str, Any]]


@router.post("/run", response_model=RunResponse)
def run(request: RunRequest) -> RunResponse:
    """Run the full repair workflow with real tool execution."""
    try:
        fetcher = FixtureIssueFetcher(request.fixture) if request.fixture else None
        repair_request = normalize_issue_input(request.input, issue_fetcher=fetcher)
        snapshot = inspect_repository(Path(request.repo))
        repo_root = str(Path(request.repo).resolve())

        test_cmd = shlex.split(request.test_cmd)
        orch = RealRepairWorkflowOrchestrator(
            validation_command=test_cmd,
            max_retries=request.max_retries,
        )

        result = orch.run(repair_request, snapshot, repo_root, diff=request.diff)

        plan_dict = asdict(result.plan) if result.plan else None
        return RunResponse(
            stage=result.state.stage.value,
            status=result.state.status.value,
            retry_count=result.state.retry_count,
            max_retries=result.state.max_retries,
            history=[s.value for s in result.state.history],
            plan=plan_dict,
            artifacts=asdict(result.artifacts),
            search_results=result.search_results,
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
