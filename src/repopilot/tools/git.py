"""Git tool with real git operations via subprocess."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy

from .contracts import ToolCategory, ToolErrorCode, ToolResult

READ_ONLY_ACTIONS = {"diff", "status", "log", "show"}
WRITE_ACTIONS = {"add", "commit", "checkout", "branch"}


class GitRequest(BaseModel):
    """Request for a git operation."""

    action: str
    repository: str = "."
    args: list[str] = []
    message: str = ""
    approved: bool = False


class RealGitTool:
    """Git tool that runs real git commands."""

    name = "git"
    category = ToolCategory.GIT
    approval_required = True

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = GitRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        repo = Path(req.repository).resolve()
        if not repo.is_dir():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Repository not found: {repo}"
            )

        if req.action in WRITE_ACTIONS:
            decision = StrictApprovalPolicy().check(ApprovalSubject.GIT, req.approved)
            if not decision.approved:
                return ToolResult.requires_approval(decision.reason)

        return self._run_git(req.action, repo, req.args, req.message)

    def _run_git(
        self, action: str, repo: Path, args: list[str], message: str
    ) -> ToolResult:
        cmd = ["git", "-C", str(repo), action]
        if action == "commit":
            if not message:
                return ToolResult.failure(
                    ToolErrorCode.INVALID_INPUT, "Commit message is required"
                )
            cmd.extend(["-m", message])
        cmd.extend(args)

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            return ToolResult.failure(
                ToolErrorCode.UNAVAILABLE, "git command not found on system"
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(ToolErrorCode.TIMEOUT, "Git command timed out")

        if completed.returncode == 0:
            return ToolResult.success(
                data={"output": completed.stdout.strip()},
                message=f"git {action} completed",
            )
        return ToolResult.failure(
            ToolErrorCode.UNKNOWN,
            f"git {action} failed: {completed.stderr.strip()}",
        )


# Backward-compatible alias
NoopGitTool = RealGitTool
