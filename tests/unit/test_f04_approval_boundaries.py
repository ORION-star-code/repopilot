from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy
from repopilot.tools import (
    NoopPatchTool,
    NoopTestRunnerTool,
    ToolErrorCode,
)


def test_strict_approval_policy_denies_by_default():
    decision = StrictApprovalPolicy().check(ApprovalSubject.PATCH)

    assert not decision.approved
    assert decision.subject == ApprovalSubject.PATCH
    assert "requires explicit approval" in decision.reason


def test_patch_tool_requires_approval_before_execution():
    result = NoopPatchTool().run(
        {
            "run_id": "run_patch",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "Fix token refresh",
        }
    )

    assert not result.ok
    assert result.approval_required
    assert result.error_code == ToolErrorCode.APPROVAL_REQUIRED


def test_patch_tool_attempts_apply_after_approval():
    result = NoopPatchTool().run(
        {
            "run_id": "run_patch",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "Fix token refresh",
            "approved": True,
        }
    )

    # Real patch tool tries to apply; may succeed or fail depending on environment
    assert not result.approval_required


def test_patch_tool_rejects_invalid_request():
    result = NoopPatchTool().run({"run_id": "run_patch"})

    assert not result.ok
    assert result.error_code == ToolErrorCode.INVALID_INPUT


def test_test_runner_requires_approval_before_execution():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["pytest", "-q"],
        }
    )

    assert not result.ok
    assert result.approval_required
    assert result.error_code == ToolErrorCode.APPROVAL_REQUIRED


def test_test_runner_executes_through_sandbox_after_approval():
    result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tests",
            "command": ["python", "-c", "print('ok')"],
            "approved": True,
        }
    )

    assert result.ok
    assert not result.approval_required
    assert result.data["executed"] is True
    assert "ok" in result.data["stdout"]


def test_test_runner_rejects_invalid_request():
    result = NoopTestRunnerTool().run({"run_id": "run_tests", "command": []})

    assert not result.ok
    assert result.error_code == ToolErrorCode.INVALID_INPUT
