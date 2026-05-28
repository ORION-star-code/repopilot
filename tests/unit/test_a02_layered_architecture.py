from pathlib import Path

from repopilot.agents import AgentRole
from repopilot.artifacts import ArtifactsWriter
from repopilot.runs import RunManager, RunStatus
from repopilot.tools import (
    NoopTestRunnerTool,
    RealFileTool,
    RealGitTool,
    RealPatchTool,
    RealSearchTool,
    ToolCategory,
    ToolErrorCode,
)
from repopilot.workflows import NoopRepairWorkflowOrchestrator, RepairRunStatus, RepairStage
from repopilot.workspace import LocalWorkspaceManager, WorkspaceSource


def test_run_manager_creates_safe_run_record():
    manager = RunManager(id_factory=lambda: "run_test")

    run = manager.start_run("https://github.com/octo/repo/issues/42", repository="octo/repo")

    assert run.run_id == "run_test"
    assert run.status == RunStatus.PENDING
    assert run.repository == "octo/repo"
    assert not run.approval_required
    assert not run.approved
    assert run.artifact_refs == []


def test_run_manager_updates_status():
    manager = RunManager(id_factory=lambda: "run_test")
    run = manager.start_run("bug")

    updated = manager.update_status(run.run_id, RunStatus.RUNNING)

    assert updated.status == RunStatus.RUNNING
    assert manager.get_run(run.run_id).status == RunStatus.RUNNING


def test_local_workspace_manager_does_not_clone_or_enable_network():
    manager = LocalWorkspaceManager(root=".")
    run = RunManager(id_factory=lambda: "run_workspace").start_run("bug", repository="octo/repo")

    workspace = manager.prepare_workspace(run)

    assert workspace.run_id == "run_workspace"
    assert workspace.source == WorkspaceSource.LOCAL
    assert workspace.path == str(Path(".").resolve())
    assert workspace.repository == "octo/repo"
    assert not workspace.cloned
    assert not workspace.network_enabled


def test_noop_orchestrator_returns_initial_workflow_state():
    run = RunManager(id_factory=lambda: "run_workflow").start_run("bug")

    state = NoopRepairWorkflowOrchestrator().start(run)

    assert state.run_id == "run_workflow"
    assert state.stage == RepairStage.INTAKE
    assert state.status == RepairRunStatus.RUNNING
    assert state.history == [RepairStage.INTAKE]


def test_agent_roles_cover_layered_architecture():
    assert {role.value for role in AgentRole} == {
        "triage",
        "planner",
        "patch",
        "failure_analyzer",
        "reviewer",
        "retrieve",
    }


def test_tool_layer_uses_categories_and_safe_defaults():
    file_result = RealFileTool().run({"action": "read", "path": "nonexistent.txt"})
    search_result = RealSearchTool().run(
        {"action": "keyword", "repository_root": ".", "query": "token"}
    )
    patch_result = RealPatchTool().run(
        {
            "run_id": "run_tools",
            "target_files": ["src/app.py"],
            "unified_diff": "diff --git a/src/app.py b/src/app.py",
            "rationale": "exercise approval boundary",
        }
    )
    test_result = NoopTestRunnerTool().run(
        {
            "run_id": "run_tools",
            "command": ["pytest"],
        }
    )
    git_result = RealGitTool().run({"action": "commit", "repository": ".", "message": "test"})

    assert RealFileTool().category == ToolCategory.FILE
    assert RealSearchTool().category == ToolCategory.SEARCH
    assert not file_result.ok
    assert file_result.error_code == ToolErrorCode.NOT_FOUND
    assert search_result.ok

    for tool_result in [patch_result, test_result, git_result]:
        assert not tool_result.ok
        assert tool_result.approval_required
        assert tool_result.error_code == ToolErrorCode.APPROVAL_REQUIRED


def test_artifact_bundle_expresses_repair_outputs():
    run = RunManager(id_factory=lambda: "run_artifacts").start_run("bug")

    bundle = ArtifactsWriter().build_bundle(
        run,
        diff="diff --git a/app.py b/app.py",
        test_report="1 passed",
        risk_assessment="low risk",
        pr_description="Fix transient auth retry",
    )

    assert bundle.run_id == "run_artifacts"
    assert bundle.diff.startswith("diff --git")
    assert bundle.test_report == "1 passed"
    assert bundle.risk_assessment == "low risk"
    assert bundle.pr_description == "Fix transient auth retry"


def test_architecture_doc_mentions_layered_flow():
    content = Path("docs/architecture.md").read_text(encoding="utf-8")

    for expected in [
        "Run Manager",
        "Workspace Manager",
        "Artifacts Writer",
        "Tool Layer",
    ]:
        assert expected in content
