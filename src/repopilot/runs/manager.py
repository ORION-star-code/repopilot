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
        """Update run status and timestamp."""
        record = self._records.get(run_id)
        if record is None:
            raise KeyError(f"Unknown run id: {run_id}")
        updated = record.model_copy(update={"status": status, "updated_at": self._clock()})
        self._records[run_id] = updated
        return updated

    def get_run(self, run_id: str) -> RunRecord:
        """Return a run record by id."""
        record = self._records.get(run_id)
        if record is None:
            raise KeyError(f"Unknown run id: {run_id}")
        return record
