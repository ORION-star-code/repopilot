"""Run records and in-memory run management for architecture wiring."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Lifecycle status for a repair run."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


# Valid status transitions
_VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.PENDING: {RunStatus.RUNNING, RunStatus.CANCELED},
    RunStatus.RUNNING: {
        RunStatus.WAITING_FOR_APPROVAL,
        RunStatus.FAILED,
        RunStatus.SUCCEEDED,
        RunStatus.CANCELED,
    },
    RunStatus.WAITING_FOR_APPROVAL: {RunStatus.RUNNING, RunStatus.CANCELED},
    RunStatus.FAILED: set(),  # terminal
    RunStatus.SUCCEEDED: set(),  # terminal
    RunStatus.CANCELED: set(),  # terminal
}


class RunRecord(BaseModel):
    """Durable record for one RepoPilot run."""

    run_id: str
    issue_input: str
    repository: str | None = None
    status: RunStatus = RunStatus.PENDING
    approval_required: bool = False
    approved: bool = False
    artifact_refs: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RunManager:
    """In-memory run manager used until persistent storage is introduced."""

    def __init__(
        self,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._id_factory = id_factory or (lambda: f"run_{uuid4().hex}")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[str, RunRecord] = {}

    def start_run(self, issue_input: str, repository: str | None = None) -> RunRecord:
        """Create a new pending run without external side effects."""
        now = self._clock()
        record = RunRecord(
            run_id=self._id_factory(),
            issue_input=issue_input,
            repository=repository,
            created_at=now,
            updated_at=now,
        )
        self._records[record.run_id] = record
        return record

    def update_status(self, run_id: str, status: RunStatus) -> RunRecord:
        """Update run status and timestamp.

        Raises ``ValueError`` if the transition is invalid or the run is terminal.
        """
        record = self._records.get(run_id)
        if record is None:
            raise KeyError(f"Unknown run id: {run_id}")

        allowed = _VALID_TRANSITIONS.get(record.status, set())
        if status not in allowed:
            raise ValueError(
                f"Invalid status transition: {record.status} -> {status}. "
                f"Allowed: {', '.join(s.value for s in allowed) or 'none (terminal)'}"
            )

        updated = record.model_copy(update={"status": status, "updated_at": self._clock()})
        self._records[run_id] = updated
        return updated

    def get_run(self, run_id: str) -> RunRecord:
        """Return a run record by id."""
        record = self._records.get(run_id)
        if record is None:
            raise KeyError(f"Unknown run id: {run_id}")
        return record

    def list_runs(self) -> list[RunRecord]:
        """Return all run records."""
        return list(self._records.values())
