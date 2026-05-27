"""Planning and artifact contracts for RepoPilot repair workflows."""

from __future__ import annotations

from .models import RepairArtifacts, RepairDryRunResult, RepairPlan, RepairRequest, RepoSnapshot

DEFAULT_MAX_RETRIES = 2


def create_repair_plan(
    request: RepairRequest,
    snapshot: RepoSnapshot,
    *,
    validation_command: str = "python scripts/check.py",
) -> RepairPlan:
    """Create a deterministic starter plan from issue and repository context."""
    target_files = snapshot.important_files[:5] if snapshot.important_files else snapshot.files[:5]
    search_hint = ", ".join(target_files) if target_files else "no indexed files yet"
    steps = [
        f"Clarify failure from request: {request.title}",
        f"Search likely code paths: {search_hint}",
        "Identify the smallest behavior-preserving fix and list files to edit.",
        "Draft the minimal patch proposal without applying it.",
        f"Plan focused validation and the complete command: {validation_command}.",
        "If validation later fails, inspect output, revise within the bounded retry policy, "
        "and rerun.",
        "Emit dry-run diff, test report, risk assessment, and PR description artifacts.",
    ]
    return RepairPlan(
        summary=f"Repair plan for {request.title}",
        target_files=target_files,
        steps=steps,
        verification=[validation_command],
    )


def empty_artifacts() -> RepairArtifacts:
    """Return the artifact contract before a real repair has run."""
    return RepairArtifacts(
        git_diff="",
        test_report="",
        risk_assessment="",
        pr_description="",
    )


def create_dry_run_artifacts(request: RepairRequest, plan: RepairPlan) -> RepairArtifacts:
    """Create deterministic no-side-effect repair artifacts."""
    target_files = ", ".join(plan.target_files) if plan.target_files else "none identified"
    return RepairArtifacts(
        git_diff="Dry run only. No files were modified.",
        test_report=(
            "Dry run only. No tests were executed. "
            f"Planned validation: {', '.join(plan.verification)}."
        ),
        risk_assessment=(
            "Low execution risk for this dry run because no patch, shell command, git operation, "
            "network request, or sandbox execution occurred. Implementation risk remains unknown "
            f"until the planned target files are reviewed: {target_files}."
        ),
        pr_description=(
            f"## Summary\nDry-run repair plan for: {request.title}\n\n"
            f"## Target Files\n{target_files}\n\n"
            "## Validation\nNo tests executed in dry-run mode.\n\n"
            "## Risk\nNo code was changed. Human review is required before any patch is applied."
        ),
    )


def run_dry_repair_workflow(
    request: RepairRequest,
    snapshot: RepoSnapshot,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> RepairDryRunResult:
    """Run the F03 dry-run repair workflow without applying patches or running tests."""
    plan = create_repair_plan(request, snapshot)
    artifacts = create_dry_run_artifacts(request, plan)
    return RepairDryRunResult(
        plan=plan,
        artifacts=artifacts,
        retry_count=0,
        max_retries=max_retries,
        approval_required=True,
        workflow_status="dry_run_completed",
    )
