"""State contracts for the RepoPilot repair workflow."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RepairStage(StrEnum):
    INTAKE = "intake"
    ANALYZE = "analyze"
    RETRIEVE = "retrieve"
    PLAN = "plan"
    PATCH = "patch"
    TEST = "test"
    REFLECT = "reflect"
    REPORT = "report"


class RepairRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


STAGE_ORDER: tuple[RepairStage, ...] = (
    RepairStage.INTAKE,
    RepairStage.ANALYZE,
    RepairStage.RETRIEVE,
    RepairStage.PLAN,
    RepairStage.PATCH,
    RepairStage.TEST,
    RepairStage.REFLECT,
    RepairStage.REPORT,
)


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
