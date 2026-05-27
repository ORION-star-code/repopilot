"""Patch tool with real patch application."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy
from repopilot.models import ExecutionMode

from .contracts import ToolCategory, ToolErrorCode, ToolResult
from .safety import contain_path

logger = logging.getLogger(__name__)

_PATCH_TIMEOUT_SECONDS = 30


class PatchProposal(BaseModel):
    """A proposed patch that has not been applied."""

    run_id: str
    target_files: list[str] = Field(min_length=1)
    unified_diff: str = Field(min_length=1)
    rationale: str
    approved: bool = False
    execution_mode: ExecutionMode = ExecutionMode.APPROVED
    working_directory: str = "."
    strip_level: int = Field(default=1, ge=0, le=10)


class PatchExecutionResult(BaseModel):
    """Structured result for patch execution."""

    applied: bool
    changed_files: list[str] = Field(default_factory=list)
    message: str


class RealPatchTool:
    """Approval-gated patch tool that applies unified diffs."""

    name = "patch"
    category = ToolCategory.PATCH
    approval_required = True

    def __init__(
        self,
        workspace_root: Path | None = None,
        policy: StrictApprovalPolicy | None = None,
    ) -> None:
        self._workspace_root = workspace_root or Path.cwd()
        self._policy = policy or StrictApprovalPolicy()

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            proposal = PatchProposal.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        decision = self._policy.check(ApprovalSubject.PATCH, proposal.approved)
        if not decision.approved:
            return ToolResult.requires_approval(decision.reason)

        if proposal.execution_mode == ExecutionMode.DRY_RUN:
            result = PatchExecutionResult(
                applied=False,
                changed_files=proposal.target_files,
                message=f"Patch dry run planned for: {', '.join(proposal.target_files)}",
            )
            return ToolResult.success(data=result.model_dump(), message=result.message)

        return self._apply_patch(proposal)

    def _apply_patch(self, proposal: PatchProposal) -> ToolResult:
        try:
            cwd = contain_path(proposal.working_directory, self._workspace_root)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))
        if not cwd.is_dir():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Working directory not found: {cwd}"
            )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".patch", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(proposal.unified_diff)
            tmp_path = tmp.name

        try:
            # Dry-run validation first
            dry_run = subprocess.run(
                [
                    "patch",
                    f"-p{proposal.strip_level}",
                    "--dry-run",
                    "--input",
                    tmp_path,
                    "--directory",
                    str(cwd),
                ],
                capture_output=True,
                text=True,
                timeout=_PATCH_TIMEOUT_SECONDS,
            )
            if dry_run.returncode != 0:
                return ToolResult.failure(
                    ToolErrorCode.UNKNOWN,
                    f"Patch validation failed (dry-run): {dry_run.stderr.strip()}",
                )

            # Actually apply the patch
            completed = subprocess.run(
                [
                    "patch",
                    f"-p{proposal.strip_level}",
                    "--input",
                    tmp_path,
                    "--directory",
                    str(cwd),
                ],
                capture_output=True,
                text=True,
                timeout=_PATCH_TIMEOUT_SECONDS,
            )
        except FileNotFoundError:
            return ToolResult.failure(
                ToolErrorCode.UNAVAILABLE, "patch command not found on system"
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(ToolErrorCode.TIMEOUT, "Patch application timed out")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if completed.returncode == 0:
            result = PatchExecutionResult(
                applied=True,
                changed_files=proposal.target_files,
                message=f"Patch applied successfully to {len(proposal.target_files)} files",
            )
            return ToolResult.success(data=result.model_dump(), message=result.message)

        result = PatchExecutionResult(
            applied=False,
            changed_files=[],
            message=f"Patch failed: {completed.stderr.strip()}",
        )
        return ToolResult.failure(ToolErrorCode.UNKNOWN, result.message)


# Backward-compatible alias
NoopPatchTool = RealPatchTool
