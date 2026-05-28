"""Intake endpoint for normalizing issue inputs."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from repopilot.issue_fetchers import FixtureIssueFetcher, IssueIntakeError
from repopilot.issue_intake import normalize_issue_input

router = APIRouter(tags=["intake"])


class IntakeRequest(BaseModel):
    """Request body for the intake endpoint."""

    input: str = Field(min_length=1, description="GitHub Issue URL or raw bug description.")
    fixture: str | None = Field(default=None, description="Path to local JSON fixture file.")


class IntakeResponse(BaseModel):
    """Response body for the intake endpoint."""

    source: str
    title: str
    body: str
    repository: str | None = None
    issue_number: int | None = None
    url: str | None = None
    labels: list[str] = []
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = {}
    raw: str | None = None


@router.post("/intake", response_model=IntakeResponse)
def intake(request: IntakeRequest) -> IntakeResponse:
    """Normalize a GitHub Issue URL or raw bug description into a structured request."""
    try:
        fetcher = FixtureIssueFetcher(request.fixture) if request.fixture else None
        result = normalize_issue_input(request.input, issue_fetcher=fetcher)
        return IntakeResponse(**asdict(result))
    except IssueIntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
