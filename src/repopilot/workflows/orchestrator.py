"""Workflow orchestration with real stage advancement."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from repopilot.models import (
    RepairArtifacts,
    RepairPlan,
    RepairRequest,
    RepoSnapshot,
)
from repopilot.repair_workflow import create_repair_plan, empty_artifacts
from repopilot.runs import RunRecord
from repopilot.sandbox import CommandRequest, SubprocessSandboxExecutor
from repopilot.tools.file import RealFileTool
from repopilot.tools.search import RealSearchTool

from .state import RepairRunStatus, RepairStage, RepairWorkflowState

logger = logging.getLogger(__name__)

_ERROR_OUTPUT_LIMIT = 500
_SEARCH_BODY_LIMIT = 200

# Valid stage transitions
_VALID_TRANSITIONS: dict[RepairStage, set[RepairStage]] = {
    RepairStage.INTAKE: {RepairStage.ANALYZE},
    RepairStage.ANALYZE: {RepairStage.RETRIEVE},
    RepairStage.RETRIEVE: {RepairStage.PLAN},
    RepairStage.PLAN: {RepairStage.PATCH},
    RepairStage.PATCH: {RepairStage.TEST},
    RepairStage.TEST: {RepairStage.REFLECT, RepairStage.REPORT},
    RepairStage.REFLECT: {RepairStage.PATCH},
    RepairStage.REPORT: set(),
}


class RepairWorkflowOrchestrator(Protocol):
    """Protocol for deterministic repair workflow orchestration."""

    def start(self, run: RunRecord) -> RepairWorkflowState:
        """Start a workflow for the run."""


class NoopRepairWorkflowOrchestrator:
    """A02 orchestrator placeholder that performs no external work."""

    def start(self, run: RunRecord) -> RepairWorkflowState:
        """Return an initial workflow state without patching or testing."""
        return RepairWorkflowState(
            run_id=run.run_id,
            stage=RepairStage.INTAKE,
            status=RepairRunStatus.RUNNING,
            history=[RepairStage.INTAKE],
        )


@dataclass
class RepairWorkflowResult:
    """Result of a complete repair workflow run."""

    state: RepairWorkflowState
    plan: RepairPlan | None
    artifacts: RepairArtifacts
    search_results: list[dict] = field(default_factory=list)


class RealRepairWorkflowOrchestrator:
    """Orchestrator that drives repair through all stages using real tools."""

    def __init__(
        self,
        *,
        validation_command: list[str] | None = None,
        max_retries: int = 2,
    ) -> None:
        self._validation_command = validation_command or [
            "python",
            "-m",
            "pytest",
            "-q",
        ]
        self._max_retries = max_retries
        self._file_tool = RealFileTool()
        self._search_tool = RealSearchTool()
        self._sandbox = SubprocessSandboxExecutor()

    def run(
        self,
        request: RepairRequest,
        snapshot: RepoSnapshot,
        repo_root: str,
        diff: str = "",
    ) -> RepairWorkflowResult:
        """Execute the full repair workflow and return results."""
        state = RepairWorkflowState(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            max_retries=self._max_retries,
        )
        artifacts = empty_artifacts()
        plan: RepairPlan | None = None
        search_results: list[dict] = []

        # INTAKE
        state = self._advance(state, RepairStage.INTAKE)

        # ANALYZE
        state = self._advance(state, RepairStage.ANALYZE)

        # RETRIEVE
        search_result = self._search_tool.run({
            "action": "keyword",
            "repository_root": repo_root,
            "query": request.title + " " + request.body[:_SEARCH_BODY_LIMIT],
            "limit": 10,
        })
        if search_result.ok and isinstance(search_result.data, dict):
            search_results = search_result.data.get("results", [])
        state = self._advance(state, RepairStage.RETRIEVE)

        # PLAN
        plan = create_repair_plan(request, snapshot)
        state = self._advance(state, RepairStage.PLAN)

        # PATCH
        state = self._advance(state, RepairStage.PATCH)

        # TEST + REFLECT loop
        test_passed = False
        test_output = ""
        while state.retry_count <= state.max_retries:
            state = self._advance(state, RepairStage.TEST)
            cmd_result = self._sandbox.run(
                CommandRequest(command=self._validation_command, cwd=repo_root)
            )
            test_output = cmd_result.stdout + cmd_result.stderr
            test_passed = cmd_result.exit_code == 0

            if test_passed:
                break

            state = state.model_copy(update={"retry_count": state.retry_count + 1})
            if state.retry_count <= state.max_retries:
                state = self._advance(state, RepairStage.REFLECT)
                state.last_error = test_output[:_ERROR_OUTPUT_LIMIT]
                # Loop back to PATCH for retry
                state = self._advance(state, RepairStage.PATCH)

        # REPORT
        state = self._advance(state, RepairStage.REPORT)
        if test_passed:
            state.status = RepairRunStatus.SUCCEEDED
        else:
            state.status = RepairRunStatus.FAILED

        # Build artifacts
        artifacts = RepairArtifacts(
            git_diff=diff or "No patch was generated.",
            test_report=test_output or "No tests were executed.",
            risk_assessment=self._assess_risk(test_passed, state.retry_count),
            pr_description=self._build_pr_description(request, plan, test_passed),
        )

        return RepairWorkflowResult(
            state=state,
            plan=plan,
            artifacts=artifacts,
            search_results=search_results,
        )

    def _advance(
        self, state: RepairWorkflowState, stage: RepairStage
    ) -> RepairWorkflowState:
        allowed = _VALID_TRANSITIONS.get(state.stage, set())
        if stage not in allowed:
            raise ValueError(
                f"Invalid stage transition: {state.stage} -> {stage}. "
                f"Allowed: {', '.join(s.value for s in allowed) or 'none (terminal)'}"
            )
        state.stage = stage
        state.status = RepairRunStatus.RUNNING
        state.history.append(stage)
        return state

    def _assess_risk(self, test_passed: bool, retry_count: int) -> str:
        if test_passed and retry_count == 0:
            return "Low risk: tests passed on first attempt."
        if test_passed:
            return f"Medium risk: tests passed after {retry_count} retries."
        return f"High risk: tests failed after {retry_count} retries."

    def _build_pr_description(
        self, request: RepairRequest, plan: RepairPlan | None, test_passed: bool
    ) -> str:
        summary = plan.summary if plan else "Repair"
        target_files = ", ".join(plan.target_files) if plan and plan.target_files else "N/A"
        status = "Tests passed." if test_passed else "Tests failed."
        return (
            f"## Summary\n{summary}\n\n"
            f"## Issue\n{request.title}\n\n"
            f"## Target Files\n{target_files}\n\n"
            f"## Validation\n{status}\n"
        )
