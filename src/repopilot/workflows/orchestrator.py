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
from repopilot.observability.events import TraceCollector, TraceEvent, TraceEventType, TraceSeverity
from repopilot.repair_workflow import create_repair_plan
from repopilot.runs import RunRecord
from repopilot.runs.manager import RunStatus
from repopilot.sandbox import CommandRequest, SubprocessSandboxExecutor
from repopilot.state_machine import StateMachine
from repopilot.tools.file import RealFileTool
from repopilot.tools.search import RealSearchTool

from .state import RepairStage, RepairWorkflowState

logger = logging.getLogger(__name__)

_ERROR_OUTPUT_LIMIT = 500
_SEARCH_BODY_LIMIT = 200

_STAGE_MACHINE = StateMachine({
    RepairStage.INTAKE: {RepairStage.ANALYZE},
    RepairStage.ANALYZE: {RepairStage.RETRIEVE},
    RepairStage.RETRIEVE: {RepairStage.PLAN},
    RepairStage.PLAN: {RepairStage.PATCH},
    RepairStage.PATCH: {RepairStage.TEST},
    RepairStage.TEST: {RepairStage.REFLECT, RepairStage.REPORT},
    RepairStage.REFLECT: {RepairStage.PATCH},
    RepairStage.REPORT: set(),
})


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
            status=RunStatus.RUNNING,
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
        collector: TraceCollector | None = None,
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
        self._collector = collector

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

        # INTAKE → ANALYZE
        state = self._advance(state, RepairStage.INTAKE)
        state = self._advance(state, RepairStage.ANALYZE)

        # RETRIEVE
        state, search_results = self._stage_retrieve(state, request, repo_root)

        # PLAN
        plan = create_repair_plan(request, snapshot)
        state = self._advance(state, RepairStage.PLAN)

        # PATCH
        state = self._advance(state, RepairStage.PATCH)

        # TEST + REFLECT loop
        state, test_passed, test_output = self._stage_test_loop(state, repo_root)

        # REPORT
        state = self._advance(state, RepairStage.REPORT)
        final_status = RunStatus.SUCCEEDED if test_passed else RunStatus.FAILED
        state = state.model_copy(update={"status": final_status})

        # Build artifacts
        artifacts = self._build_artifacts(request, plan, test_passed, test_output, state, diff)

        return RepairWorkflowResult(
            state=state,
            plan=plan,
            artifacts=artifacts,
            search_results=search_results,
        )

    def _stage_retrieve(
        self,
        state: RepairWorkflowState,
        request: RepairRequest,
        repo_root: str,
    ) -> tuple[RepairWorkflowState, list[dict]]:
        """Execute RETRIEVE stage and return updated state with search results."""
        search_result = self._search_tool.run({
            "action": "keyword",
            "repository_root": repo_root,
            "query": request.title + " " + request.body[:_SEARCH_BODY_LIMIT],
            "limit": 10,
        })
        search_results: list[dict] = []
        if search_result.ok and isinstance(search_result.data, dict):
            search_results = search_result.data.get("results", [])

        if self._collector:
            self._collector.record(TraceEvent(
                run_id=state.run_id,
                event_type=TraceEventType.TOOL_CALL,
                message=f"Search returned {len(search_results)} results",
                metadata={"tool": "search", "query_length": len(request.title)},
            ))

        state = self._advance(state, RepairStage.RETRIEVE)
        return state, search_results

    def _stage_test_loop(
        self,
        state: RepairWorkflowState,
        repo_root: str,
    ) -> tuple[RepairWorkflowState, bool, str]:
        """Execute TEST+REFLECT retry loop and return final state, pass status, and output."""
        test_passed = False
        test_output = ""

        while state.retry_count <= state.max_retries:
            state = self._advance(state, RepairStage.TEST)
            cmd_result = self._sandbox.run(
                CommandRequest(command=self._validation_command, cwd=repo_root)
            )
            test_output = cmd_result.stdout + cmd_result.stderr
            test_passed = cmd_result.exit_code == 0

            if self._collector:
                self._collector.record(TraceEvent(
                    run_id=state.run_id,
                    event_type=TraceEventType.SANDBOX_EXECUTION,
                    message=f"Sandbox exit_code={cmd_result.exit_code}",
                    severity=TraceSeverity.INFO if test_passed else TraceSeverity.WARNING,
                    metadata={"exit_code": cmd_result.exit_code},
                ))

            if test_passed:
                break

            state = state.model_copy(update={"retry_count": state.retry_count + 1})
            if self._collector:
                self._collector.record(TraceEvent(
                    run_id=state.run_id,
                    event_type=TraceEventType.RETRY,
                    message=f"Test failed, retry {state.retry_count}/{state.max_retries}",
                    severity=TraceSeverity.WARNING,
                    metadata={"retry_count": state.retry_count},
                ))
            if state.retry_count <= state.max_retries:
                state = self._advance(state, RepairStage.REFLECT)
                state = state.model_copy(update={"last_error": test_output[:_ERROR_OUTPUT_LIMIT]})
                state = self._advance(state, RepairStage.PATCH)

        return state, test_passed, test_output

    def _build_artifacts(
        self,
        request: RepairRequest,
        plan: RepairPlan | None,
        test_passed: bool,
        test_output: str,
        state: RepairWorkflowState,
        diff: str,
    ) -> RepairArtifacts:
        """Build repair artifacts from workflow results."""
        artifacts = RepairArtifacts(
            git_diff=diff or "No patch was generated.",
            test_report=test_output or "No tests were executed.",
            risk_assessment=self._assess_risk(test_passed, state.retry_count),
            pr_description=self._build_pr_description(request, plan, test_passed),
        )

        if self._collector:
            self._collector.record(TraceEvent(
                run_id=state.run_id,
                event_type=TraceEventType.ARTIFACT_WRITE,
                message=f"Built {len(artifacts.git_diff)} char diff, "
                        f"risk={artifacts.risk_assessment[:50]}",
                metadata={"diff_length": len(artifacts.git_diff)},
            ))

        return artifacts

    def _advance(
        self, state: RepairWorkflowState, stage: RepairStage
    ) -> RepairWorkflowState:
        _STAGE_MACHINE.validate(state.stage, stage)
        new_state = state.model_copy(update={
            "stage": stage,
            "status": RunStatus.RUNNING,
            "history": [*state.history, stage],
        })
        if self._collector:
            self._collector.record(TraceEvent(
                run_id=state.run_id,
                event_type=TraceEventType.STAGE_TRANSITION,
                message=f"{state.stage} -> {stage}",
                metadata={"from": state.stage.value, "to": stage.value},
            ))
        return new_state

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
