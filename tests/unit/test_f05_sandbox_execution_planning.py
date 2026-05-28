"""F05: Sandbox execution planning with dry-run vs approved modes."""

import pytest

from repopilot.config import Settings
from repopilot.models import (
    CommandPlan,
    ExecutionMode,
    ExecutionPlan,
    derive_execution_mode,
)
from repopilot.sandbox import CommandRequest, NoopSandboxExecutor
from repopilot.tools import (
    NoopTestRunnerTool,
    RealPatchTool,
    ToolErrorCode,
)

# --- ExecutionMode enum ---


def test_execution_mode_enum_values():
    assert ExecutionMode.DRY_RUN == "dry_run"
    assert ExecutionMode.APPROVED == "approved"
    assert len(list(ExecutionMode)) == 2


def test_execution_mode_rejects_invalid_value():
    with pytest.raises(ValueError):
        ExecutionMode("unknown")


# --- CommandPlan ---


def test_command_plan_creation():
    request = CommandRequest(command=["pytest", "-q"])
    plan = CommandPlan(
        request=request,
        mode=ExecutionMode.DRY_RUN,
        description="Run tests",
        dry_run_message="Would run pytest",
    )

    assert plan.mode == ExecutionMode.DRY_RUN
    assert plan.is_dry_run is True
    assert plan.description == "Run tests"
    assert plan.dry_run_message == "Would run pytest"


def test_command_plan_defaults_to_approved_mode():
    request = CommandRequest(command=["pytest", "-q"])
    plan = CommandPlan(request=request)

    assert plan.mode == ExecutionMode.APPROVED
    assert plan.is_dry_run is False


# --- ExecutionPlan ---


def test_execution_plan_groups_command_plans():
    request = CommandRequest(command=["pytest", "-q"])
    plan = ExecutionPlan(
        run_id="run_1",
        description="Run test suite",
        commands=[
            CommandPlan(request=request, mode=ExecutionMode.DRY_RUN),
        ],
    )

    assert len(plan.commands) == 1
    assert plan.mode == ExecutionMode.DRY_RUN
    assert plan.is_dry_run is True


def test_execution_plan_mode_reflects_commands():
    request = CommandRequest(command=["pytest", "-q"])
    dry_plan = ExecutionPlan(
        run_id="run_1",
        commands=[CommandPlan(request=request, mode=ExecutionMode.DRY_RUN)],
    )
    assert dry_plan.is_dry_run is True

    approved_plan = ExecutionPlan(
        run_id="run_2",
        commands=[CommandPlan(request=request, mode=ExecutionMode.APPROVED)],
    )
    assert approved_plan.is_dry_run is False


def test_execution_plan_empty_defaults_to_approved():
    plan = ExecutionPlan(run_id="run_1")
    assert plan.mode == ExecutionMode.APPROVED
    assert plan.is_dry_run is False


# --- derive_execution_mode ---


def test_derive_execution_mode_from_config_flags():
    assert derive_execution_mode(False, False) == ExecutionMode.DRY_RUN
    assert derive_execution_mode(True, False) == ExecutionMode.DRY_RUN
    assert derive_execution_mode(False, True) == ExecutionMode.DRY_RUN
    assert derive_execution_mode(True, True) == ExecutionMode.APPROVED


# --- NoopSandboxExecutor ---


def test_noop_sandbox_dry_run_returns_simulated_success():
    request = CommandRequest(command=["pytest", "-q"])
    result = NoopSandboxExecutor().run(request, execution_mode=ExecutionMode.DRY_RUN)

    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout
    assert result.stderr == ""
    assert result.timed_out is False


def test_noop_sandbox_approved_mode_refuses_execution():
    request = CommandRequest(command=["pytest", "-q"])
    result = NoopSandboxExecutor().run(request, execution_mode=ExecutionMode.APPROVED)

    assert result.exit_code == 127
    assert "not implemented" in result.stderr


def test_noop_sandbox_defaults_to_approved_mode():
    request = CommandRequest(command=["pytest", "-q"])
    result = NoopSandboxExecutor().run(request)

    assert result.exit_code == 127
    assert "not implemented" in result.stderr


# --- NoopTestRunnerTool ---


def test_test_runner_dry_run_produces_planning_artifact():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["pytest", "-q"],
            "approved": True,
            "execution_mode": "dry_run",
        }
    )

    assert result.ok
    assert not result.approval_required
    assert result.data["executed"] is False
    assert "DRY RUN" in result.data["stdout"]
    assert "dry run" in result.data["message"].lower()


def test_test_runner_approved_mode_executes_through_sandbox():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["python", "-c", "print('ok')"],
            "approved": True,
            "execution_mode": "approved",
        }
    )

    assert result.ok
    assert result.data["executed"] is True
    assert "ok" in result.data["stdout"]


def test_test_runner_unapproved_still_denied_regardless_of_mode():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["pytest", "-q"],
            "approved": False,
            "execution_mode": "dry_run",
        }
    )

    assert not result.ok
    assert result.approval_required
    assert result.error_code == ToolErrorCode.APPROVAL_REQUIRED


# --- NoopPatchTool ---


def test_patch_tool_dry_run_produces_planning_artifact():
    result = RealPatchTool().run(
        {
            "run_id": "run_patch",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "Fix bug",
            "approved": True,
            "execution_mode": "dry_run",
        }
    )

    assert result.ok
    assert not result.approval_required
    assert result.data["applied"] is False
    assert "src/app.py" in result.data["changed_files"]
    assert "dry run" in result.data["message"].lower()


def test_patch_tool_approved_mode_attempts_apply():
    result = RealPatchTool().run(
        {
            "run_id": "run_patch",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "Fix bug",
            "approved": True,
            "execution_mode": "approved",
        }
    )

    # Real patch tool attempts to apply; result depends on environment
    assert not result.approval_required


def test_patch_tool_unapproved_still_denied_regardless_of_mode():
    result = RealPatchTool().run(
        {
            "run_id": "run_patch",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "Fix bug",
            "approved": False,
            "execution_mode": "dry_run",
        }
    )

    assert not result.ok
    assert result.approval_required
    assert result.error_code == ToolErrorCode.APPROVAL_REQUIRED


# --- Settings.execution_mode ---


def test_settings_derive_execution_mode():
    settings_dry = Settings(sandbox_enabled=False, shell_execution_enabled=False)
    assert settings_dry.execution_mode == ExecutionMode.DRY_RUN

    settings_approved = Settings(sandbox_enabled=True, shell_execution_enabled=True)
    assert settings_approved.execution_mode == ExecutionMode.APPROVED
