"""Inspect endpoint for repository analysis."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from repopilot.repo_analysis import inspect_repository

router = APIRouter(tags=["inspect"])


class InspectRequest(BaseModel):
    """Request body for the inspect endpoint."""

    path: str = Field(default=".", description="Repository path to inspect.")


class RepoFileResponse(BaseModel):
    """Response model for a single file detail."""

    path: str
    suffix: str
    size_bytes: int
    line_count: int
    category: str


class InspectResponse(BaseModel):
    """Response body for the inspect endpoint."""

    root: str
    files: list[str]
    language_counts: dict[str, int] = {}
    file_details: list[RepoFileResponse] = []
    test_files: list[str] = []
    config_files: list[str] = []
    entrypoint_files: list[str] = []
    important_files: list[str] = []


@router.post("/inspect", response_model=InspectResponse)
def inspect(request: InspectRequest) -> InspectResponse:
    """Inspect a local repository tree and return structured snapshot."""
    try:
        snapshot = inspect_repository(Path(request.path))
        data = asdict(snapshot)
        return InspectResponse(**data)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
