"""Git tool with real git operations via subprocess."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy

from .contracts import ToolCategory, ToolErrorCode, ToolResult
from .safety import contain_path, sanitize_git_args

logger = logging.getLogger(__name__)

READ_ONLY_ACTIONS = {"diff", "status", "log", "show", "rev-parse", "remote"}
WRITE_ACTIONS = {
    "add",
    "commit",
    "checkout",
    "branch",
    "push",
    "reset",
    "clean",
    "stash",
    "merge",
    "rebase",
}
ALL_ACTIONS = READ_ONLY_ACTIONS | WRITE_ACTIONS
_GIT_TIMEOUT_SECONDS = 30


class GitRequest(BaseModel):
    """Request for a git operation."""

    action: str
    repository: str = "."
    args: list[str] = Field(default_factory=list)
    message: str = Field(default="", max_length=10000)
    approved: bool = False


class RealGitTool:
    """Git tool that runs real git commands."""

    name = "git"
    category = ToolCategory.GIT
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
            req = GitRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        if req.action not in ALL_ACTIONS:
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT,
                f"Unknown git action: {req.action!r}. "
                f"Allowed: {', '.join(sorted(ALL_ACTIONS))}",
            )

        try:
            sanitize_git_args(req.args)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        try:
            repo = contain_path(req.repository, self._workspace_root)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))
        if not repo.is_dir():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Repository not found: {repo}"
            )

        if req.action in WRITE_ACTIONS:
            decision = self._policy.check(ApprovalSubject.GIT, req.approved)
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
                timeout=_GIT_TIMEOUT_SECONDS,
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


def __getattr__(name: str) -> type:
    if name == "NoopGitTool":
        import warnings
        warnings.warn(
            "NoopGitTool is deprecated, use RealGitTool instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return RealGitTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
