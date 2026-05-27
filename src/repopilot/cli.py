"""Command-line entrypoints for RepoPilot."""

from __future__ import annotations

import argparse
import json
import logging
import shlex
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

from .artifacts.writer import ArtifactBundle, ArtifactsWriter
from .config import get_settings
from .issue_fetchers import FixtureIssueFetcher
from .issue_intake import normalize_issue_input
from .repair_workflow import create_repair_plan, run_dry_repair_workflow
from .repo_analysis import inspect_repository
from .runs.manager import RunStatus
from .workflows.orchestrator import RealRepairWorkflowOrchestrator

logger = logging.getLogger(__name__)

OUTPUT_TRUNCATION_LIMIT = 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repopilot",
        description="Issue-driven repository repair assistant.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subcommands = parser.add_subparsers(dest="command")

    intake = subcommands.add_parser("intake", help="Normalize an issue URL or bug description.")
    intake.add_argument("input", help="GitHub Issue URL or raw bug description.")
    intake.add_argument(
        "--fixture",
        help="Load complete GitHub Issue fields from a local JSON fixture. No network is used.",
    )

    inspect = subcommands.add_parser("inspect", help="Inspect a local repository tree.")
    inspect.add_argument("path", nargs="?", default=".", help="Repository path to inspect.")

    plan = subcommands.add_parser(
        "plan",
        help="Create a starter repair plan from input and repository context.",
    )
    plan.add_argument("input", help="GitHub Issue URL or raw bug description.")
    plan.add_argument("--repo", default=".", help="Repository path to inspect.")

    dry_run = subcommands.add_parser(
        "dry-run",
        help="Run the no-side-effect repair workflow and emit planned artifacts.",
    )
    dry_run.add_argument("input", help="GitHub Issue URL or raw bug description.")
    dry_run.add_argument("--repo", default=".", help="Repository path to inspect.")
    dry_run.add_argument(
        "--fixture",
        help="Load complete GitHub Issue fields from a local JSON fixture. No network is used.",
    )

    run = subcommands.add_parser(
        "run",
        help="Run the full repair workflow with real tool execution.",
    )
    run.add_argument("input", help="GitHub Issue URL or raw bug description.")
    run.add_argument("--repo", default=".", help="Repository path to repair.")
    run.add_argument("--diff", default="", help="Unified diff to apply (or path to .patch file).")
    run.add_argument("--test-cmd", default="python -m pytest -q", help="Validation command.")
    run.add_argument("--max-retries", type=int, default=2, help="Max retry attempts.")
    run.add_argument("--output", default="", help="Directory to save artifacts.")
    run.add_argument("--fixture", help="Load issue from local JSON fixture.")

    return parser


def _truncate(text: str, limit: int = OUTPUT_TRUNCATION_LIMIT) -> str:
    if len(text) > limit:
        return text[:limit] + "... (truncated)"
    return text


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(name)s %(levelname)s: %(message)s")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "intake":
        try:
            fetcher = FixtureIssueFetcher(args.fixture) if args.fixture else None
            request = normalize_issue_input(args.input, issue_fetcher=fetcher)
            print(json.dumps(asdict(request), indent=2))
            return 0
        except (ValueError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "inspect":
        try:
            snapshot = inspect_repository(Path(args.path))
            print(json.dumps(asdict(snapshot), indent=2))
            return 0
        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "plan":
        try:
            request = normalize_issue_input(args.input)
            snapshot = inspect_repository(Path(args.repo))
            plan = create_repair_plan(request, snapshot)
            print(json.dumps(asdict(plan), indent=2))
            return 0
        except (ValueError, FileNotFoundError, NotADirectoryError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "dry-run":
        try:
            fetcher = FixtureIssueFetcher(args.fixture) if args.fixture else None
            request = normalize_issue_input(args.input, issue_fetcher=fetcher)
            snapshot = inspect_repository(Path(args.repo))
            result = run_dry_repair_workflow(request, snapshot)
            print(json.dumps(asdict(result), indent=2))
            return 0
        except (ValueError, FileNotFoundError, NotADirectoryError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "run":
        return _run_repair(args)

    parser.print_help()
    return 0


def _run_repair(args: argparse.Namespace) -> int:
    try:
        fetcher = FixtureIssueFetcher(args.fixture) if args.fixture else None
        request = normalize_issue_input(args.input, issue_fetcher=fetcher)
        snapshot = inspect_repository(Path(args.repo))
        repo_root = str(Path(args.repo).resolve())

        # Load diff from file if provided
        diff = args.diff
        if diff and Path(diff).is_file():
            diff = Path(diff).read_text(encoding="utf-8")

        test_cmd = shlex.split(args.test_cmd)
        orch = RealRepairWorkflowOrchestrator(
            validation_command=test_cmd,
            max_retries=args.max_retries,
        )

        result = orch.run(request, snapshot, repo_root, diff=diff)

        # Print summary
        print(f"Stage: {result.state.stage}")
        print(f"Status: {result.state.status}")
        print(f"Retries: {result.state.retry_count}/{result.state.max_retries}")
        print(f"History: {' -> '.join(result.state.history)}")
        print()

        # Save artifacts if output dir specified
        if args.output:
            writer = ArtifactsWriter()
            run_id = f"cli-{uuid.uuid4().hex[:8]}"
            bundle = ArtifactBundle(
                run_id=run_id,
                diff=result.artifacts.git_diff,
                test_report=result.artifacts.test_report,
                risk_assessment=result.artifacts.risk_assessment,
                pr_description=result.artifacts.pr_description,
            )
            written = writer.save_to_disk(bundle, args.output)
            print(f"Artifacts saved to: {args.output}")
            for f in written:
                print(f"  {f}")
        else:
            # Print artifacts to stdout
            print("=== Test Report ===")
            print(_truncate(result.artifacts.test_report))
            print()
            print("=== Risk Assessment ===")
            print(_truncate(result.artifacts.risk_assessment))
            print()
            print("=== PR Description ===")
            print(_truncate(result.artifacts.pr_description))

        return 0 if result.state.status == RunStatus.SUCCEEDED else 1

    except (ValueError, FileNotFoundError, NotADirectoryError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
