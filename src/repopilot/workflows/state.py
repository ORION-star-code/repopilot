"""State contracts for the RepoPilot repair workflow."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from repopilot.runs.manager import RunStatus


class RepairStage(StrEnum):
    INTAKE = "intake"
    ANALYZE = "analyze"
    RETRIEVE = "retrieve"
    PLAN = "plan"
    PATCH = "patch"
    TEST = "test"
    REFLECT = "reflect"
    REPORT = "report"


# Backward-compatible alias — canonical type is RunStatus
RepairRunStatus = RunStatus


STAGE_ORDER: tuple[RepairStage, ...] = tuple(RepairStage)


class RepairWorkflowState(BaseModel):
    """Durable state summary for one repair run."""

    run_id: str
    stage: RepairStage = RepairStage.INTAKE
    status: RepairRunStatus = RepairRunStatus.PENDING
    retry_count: int = 0
    max_retries: int = 2
    approval_required: bool = False
    history: list[RepairStage] = Field(default_factory=list)
    last_error: str | None = None
