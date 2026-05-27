"""Test runner tool boundary."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy
from repopilot.models import ExecutionMode
from repopilot.sandbox import CommandRequest, SubprocessSandboxExecutor

from .contracts import ToolCategory, ToolErrorCode, ToolResult

logger = logging.getLogger(__name__)


class TestExecutionRequest(BaseModel):
    """Request to execute tests through a future sandbox."""

    run_id: str
    command: list[str] = Field(min_length=1)
    cwd: str | None = None
    timeout_seconds: int = Field(default=120, ge=1, le=1800)
    network_enabled: bool = False
    approved: bool = False
    execution_mode: ExecutionMode = ExecutionMode.APPROVED


class TestExecutionResult(BaseModel):
    """Structured result for future sandboxed test execution."""

    executed: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    message: str


class NoopTestRunnerTool:
    """Approval-gated test execution boundary with dry-run and approved modes."""

    name = "noop_test_runner"
    category = ToolCategory.TEST
    approval_required = True

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            request = TestExecutionRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        decision = StrictApprovalPolicy().check(ApprovalSubject.TEST_EXECUTION, request.approved)
        if not decision.approved:
            return ToolResult.requires_approval(decision.reason)

        if request.execution_mode == ExecutionMode.DRY_RUN:
            result = TestExecutionResult(
                executed=False,
                exit_code=0,
                stdout=f"DRY RUN: would execute {' '.join(request.command)}",
                message=f"Test dry run planned. Command: {' '.join(request.command)}",
            )
            return ToolResult.success(data=result.model_dump(), message=result.message)

        sandbox = SubprocessSandboxExecutor()
        cmd_request = CommandRequest(
            command=request.command,
            cwd=request.cwd,
            timeout_seconds=request.timeout_seconds,
            network_enabled=request.network_enabled,
        )
        cmd_result = sandbox.run(cmd_request, execution_mode=request.execution_mode)
        result = TestExecutionResult(
            executed=(cmd_result.exit_code == 0),
            exit_code=cmd_result.exit_code,
            stdout=cmd_result.stdout,
            stderr=cmd_result.stderr,
            message=(
                "Test executed successfully."
                if cmd_result.exit_code == 0
                else "Test execution failed."
            ),
        )
        if cmd_result.exit_code == 0:
            return ToolResult.success(data=result.model_dump(), message=result.message)
        return ToolResult.failure(ToolErrorCode.UNKNOWN, result.message)
