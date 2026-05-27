"""F06: Real subprocess sandbox executor."""

from repopilot.models import ExecutionMode
from repopilot.sandbox import CommandRequest, SubprocessSandboxExecutor
from repopilot.tools import NoopTestRunnerTool, ToolErrorCode

# --- SubprocessSandboxExecutor ---


def test_subprocess_sandbox_executes_real_command():
    request = CommandRequest(command=["python", "-c", "print('hello')"])
    result = SubprocessSandboxExecutor().run(request)

    assert result.exit_code == 0
    assert "hello" in result.stdout
    assert result.timed_out is False


def test_subprocess_sandbox_captures_stderr():
    request = CommandRequest(command=["python", "-c", "import sys; sys.stderr.write('err')"])
    result = SubprocessSandboxExecutor().run(request)

    assert result.exit_code == 0
    assert "err" in result.stderr


def test_subprocess_sandbox_returns_nonzero_exit_code():
    request = CommandRequest(command=["python", "-c", "import sys; sys.exit(1)"])
    result = SubprocessSandboxExecutor().run(request)

    assert result.exit_code == 1


def test_subprocess_sandbox_timeout():
    request = CommandRequest(
        command=["python", "-c", "import time; time.sleep(10)"],
        timeout_seconds=1,
    )
    result = SubprocessSandboxExecutor().run(request)

    assert result.timed_out is True
    assert result.exit_code == -1
    assert "timed out" in result.stderr


def test_subprocess_sandbox_command_not_found():
    request = CommandRequest(command=["nonexistent_command_xyz"])
    result = SubprocessSandboxExecutor().run(request)

    assert result.exit_code == 127
    assert "not found" in result.stderr


def test_subprocess_sandbox_dry_run_returns_simulated():
    request = CommandRequest(command=["python", "-c", "print('hello')"])
    result = SubprocessSandboxExecutor().run(request, execution_mode=ExecutionMode.DRY_RUN)

    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout


def test_subprocess_sandbox_with_cwd():
    # Use a relative path within the workspace to pass contain_path validation
    request = CommandRequest(
        command=["python", "-c", "import os; print(os.getcwd())"],
        cwd="tests",
    )
    result = SubprocessSandboxExecutor().run(request)

    assert result.exit_code == 0
    assert "tests" in result.stdout.strip().replace("\\", "/").lower()


# --- Test runner integration ---


def test_test_runner_approved_mode_now_executes():
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


def test_test_runner_dry_run_still_returns_planning_artifact():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["python", "-c", "print('ok')"],
            "approved": True,
            "execution_mode": "dry_run",
        }
    )

    assert result.ok
    assert result.data["executed"] is False
    assert "DRY RUN" in result.data["stdout"]


def test_test_runner_unapproved_still_denied():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["python", "-c", "print('ok')"],
            "approved": False,
        }
    )

    assert not result.ok
    assert result.approval_required
    assert result.error_code == ToolErrorCode.APPROVAL_REQUIRED
