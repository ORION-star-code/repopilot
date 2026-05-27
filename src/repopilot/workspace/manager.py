"""Workspace references for local and future cloned repositories."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from repopilot.runs import RunRecord


class WorkspaceSource(StrEnum):
    """Origin of a prepared workspace."""

    LOCAL = "local"
    GITHUB_CLONE = "github_clone"
    FIXTURE = "fixture"


class WorkspaceRef(BaseModel):
    """Reference to a prepared workspace."""

    run_id: str
    source: WorkspaceSource
    path: str | None = None
    repository: str | None = None
    cloned: bool = False
    network_enabled: bool = False


class WorkspaceManager(Protocol):
    """Protocol for preparing isolated workspaces."""

    def prepare_workspace(self, run: RunRecord) -> WorkspaceRef:
        """Prepare or reference a workspace for the run."""


class LocalWorkspaceManager:
    """No-clone workspace manager for local development and architecture tests."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root else None

    def prepare_workspace(self, run: RunRecord) -> WorkspaceRef:
        """Return a local workspace reference without cloning or network access."""
        return WorkspaceRef(
            run_id=run.run_id,
            source=WorkspaceSource.LOCAL,
            path=str(self.root) if self.root else None,
            repository=run.repository,
            cloned=False,
            network_enabled=False,
        )
