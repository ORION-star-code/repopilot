"""Sandbox execution contracts."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from repopilot.models import ExecutionMode

logger = logging.getLogger(__name__)


class CommandRequest(BaseModel):
    """Command request for future Docker-backed execution."""

    command: list[str] = Field(min_length=1)
    cwd: str | None = None
    timeout_seconds: int = 60
    network_enabled: bool = False


class CommandResult(BaseModel):
    """Structured command execution result."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class SandboxExecutor(Protocol):
    """Protocol for isolated command execution."""

    def run(
        self,
        request: CommandRequest,
        execution_mode: ExecutionMode = ExecutionMode.APPROVED,
    ) -> CommandResult:
        """Run a command in an isolated workspace."""


class NoopSandboxExecutor:
    """Executor placeholder that never runs user-controlled commands."""

    def run(
        self,
        request: CommandRequest,
        execution_mode: ExecutionMode = ExecutionMode.APPROVED,
    ) -> CommandResult:
        if execution_mode == ExecutionMode.DRY_RUN:
            return CommandResult(
                exit_code=0,
                stdout=f"DRY RUN: would execute {' '.join(request.command)}",
            )
        return CommandResult(
            exit_code=127,
            stderr=(
                "Sandbox execution is not implemented. "
                f"Refused command: {' '.join(request.command)}"
            ),
        )


def _sanitize_env() -> dict[str, str]:
    """Return a copy of os.environ with REPOPILOT_* variables removed."""
    return {k: v for k, v in os.environ.items() if not k.startswith("REPOPILOT_")}


class SubprocessSandboxExecutor:
    """Executor that runs commands via subprocess with safety constraints."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root or Path.cwd()

    def _validate_cwd(self, cwd: str | None) -> str | None:
        """Validate that cwd stays within the workspace root."""
        if cwd is None:
            return None
        root = self._workspace_root.resolve()
        resolved = (root / cwd).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"cwd {cwd!r} escapes workspace root {root}")
        return str(resolved)

    def run(
        self,
        request: CommandRequest,
        execution_mode: ExecutionMode = ExecutionMode.APPROVED,
    ) -> CommandResult:
        if execution_mode == ExecutionMode.DRY_RUN:
            return CommandResult(
                exit_code=0,
                stdout=f"DRY RUN: would execute {' '.join(request.command)}",
            )
        try:
            validated_cwd = self._validate_cwd(request.cwd)
        except ValueError as exc:
            return CommandResult(exit_code=126, stderr=str(exc))
        try:
            completed = subprocess.run(
                request.command,
                cwd=validated_cwd,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                env=_sanitize_env(),
            )
            return CommandResult(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                exit_code=-1,
                timed_out=True,
                stderr=f"Command timed out after {request.timeout_seconds}s",
            )
        except FileNotFoundError:
            return CommandResult(
                exit_code=127,
                stderr=f"Command not found: {request.command[0]}",
            )
        except OSError as exc:
            return CommandResult(
                exit_code=126,
                stderr=f"OS error: {exc}",
            )
