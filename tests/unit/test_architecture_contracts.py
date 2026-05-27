import importlib

from repopilot.config import Settings
from repopilot.tools import ToolErrorCode, ToolResult
from repopilot.workflows import STAGE_ORDER, RepairStage, RepairWorkflowState


def test_settings_default_to_safe_local_mode():
    settings = Settings()

    assert settings.environment == "local"
    assert not settings.sandbox_network_enabled
    assert not settings.github_writes_enabled
    assert not settings.shell_execution_enabled
    assert settings.high_risk_actions_require_approval


def test_tool_result_expresses_success_failure_and_approval():
    success = ToolResult.success({"path": "src/repopilot"})
    failure = ToolResult.failure(ToolErrorCode.PERMISSION_DENIED, "write disabled")
    approval = ToolResult.requires_approval("opening a PR requires approval")

    assert success.ok
    assert success.data == {"path": "src/repopilot"}
    assert not failure.ok
    assert failure.error_code == ToolErrorCode.PERMISSION_DENIED
    assert approval.approval_required
    assert approval.error_code == ToolErrorCode.APPROVAL_REQUIRED


def test_workflow_stage_order_covers_main_repair_path():
    assert [stage.value for stage in STAGE_ORDER] == [
        "intake",
        "analyze",
        "retrieve",
        "plan",
        "patch",
        "test",
        "reflect",
        "report",
    ]

    state = RepairWorkflowState(run_id="run_001")
    assert state.stage == RepairStage.INTAKE
    assert state.retry_count == 0


def test_target_architecture_packages_are_importable():
    for module_name in [
        "repopilot.api",
        "repopilot.agents",
        "repopilot.approvals",
        "repopilot.artifacts",
        "repopilot.workflows",
        "repopilot.tools",
        "repopilot.github",
        "repopilot.runs",
        "repopilot.sandbox",
        "repopilot.workspace",
        "repopilot.retrieval",
        "repopilot.observability",
        "repopilot.evaluation",
    ]:
        assert importlib.import_module(module_name)
