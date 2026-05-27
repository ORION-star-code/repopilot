"""Shared data contracts for the RepoPilot workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class RepairRequest:
    source: str
    title: str
    body: str
    repository: str | None = None
    issue_number: int | None = None
    url: str | None = None
    labels: list[str] = field(default_factory=list)
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: str | None = None


@dataclass(frozen=True)
class RepoFile:
    path: str
    suffix: str
    size_bytes: int
    line_count: int
    category: str


@dataclass(frozen=True)
class RepoSnapshot:
    root: str
    files: tuple[str, ...]
    language_counts: dict[str, int] = field(default_factory=dict)
    file_details: tuple[RepoFile, ...] = ()
    test_files: tuple[str, ...] = ()
    config_files: tuple[str, ...] = ()
    entrypoint_files: tuple[str, ...] = ()
    important_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepairPlan:
    summary: str
    target_files: tuple[str, ...]
    steps: tuple[str, ...]
    verification: tuple[str, ...]


@dataclass(frozen=True)
class RepairArtifacts:
    git_diff: str
    test_report: str
    pr_description: str
    risk_assessment: str = ""


@dataclass(frozen=True)
class RepairDryRunResult:
    plan: RepairPlan
    artifacts: RepairArtifacts
    retry_count: int
    max_retries: int
    approval_required: bool
    workflow_status: str


class ExecutionMode(StrEnum):
    """Execution mode for sandbox commands."""

    DRY_RUN = "dry_run"
    APPROVED = "approved"


def derive_execution_mode(
    sandbox_enabled: bool,
    shell_execution_enabled: bool,
) -> ExecutionMode:
    """Derive execution mode from config flags.

    Returns APPROVED only when both sandbox and shell execution are enabled.
    Otherwise returns DRY_RUN for safety.
    """
    if sandbox_enabled and shell_execution_enabled:
        return ExecutionMode.APPROVED
    return ExecutionMode.DRY_RUN


class CommandPlan(BaseModel):
    """A single planned command with execution mode."""

    request: Any  # CommandRequest at runtime; Any avoids circular import
    mode: ExecutionMode = ExecutionMode.APPROVED
    description: str = ""
    dry_run_message: str = ""

    @property
    def is_dry_run(self) -> bool:
        """Return True if this plan is in dry-run mode."""
        return self.mode == ExecutionMode.DRY_RUN


class ExecutionPlan(BaseModel):
    """A sequence of command plans for a repair workflow step."""

    run_id: str
    description: str = ""
    commands: list[CommandPlan] = []

    @property
    def mode(self) -> ExecutionMode:
        """Return the execution mode of the first command."""
        if not self.commands:
            return ExecutionMode.APPROVED
        return self.commands[0].mode

    @property
    def is_dry_run(self) -> bool:
        """Return True if this plan is in dry-run mode."""
        return self.mode == ExecutionMode.DRY_RUN
