# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RepoPilot is an AI coding agent for issue-driven GitHub repository repair. It reads a bug report, analyzes the repo, creates a repair plan, applies patches, runs tests, and produces a PR. The project prioritizes safety, approval gates, deterministic orchestration, and observability.

## Commands

```bash
# Install (editable + dev deps)
python -m pip install -e ".[dev]"

# Run all checks (lint + type check + tests + harness validation)
python scripts/check.py

# Individual checks
python scripts/lint.py          # ruff + mypy
python -m pytest -q             # tests
python harness/validate.py      # harness contract checks

# CLI preview
python scripts/repopilot.py --help

# API preview (FastAPI)
uvicorn repopilot.main:app --reload

# Make shortcuts (if available): make setup, make dev, make test, make lint, make check
```

## Architecture

Layered flow: CLI/API → Run Manager → Repair Workflow Orchestrator → subsystems → Artifacts.

- **src/repopilot/** — main package
  - `cli.py`, `main.py` — CLI and FastAPI entrypoints
  - `config.py` — Pydantic settings
  - `models.py` — shared Pydantic models
  - `issue_intake.py`, `issue_fetchers.py` — normalize bug input (raw text, GitHub URL, fixtures)
  - `repo_analysis.py` — local repo snapshot and file classification
  - `repair_workflow.py` — dry-run repair plan orchestrator
  - `runs/manager.py` — run lifecycle (status, timestamps, approval state)
  - `workspace/manager.py` — workspace preparation (local/noop)
  - `workflows/orchestrator.py` — deterministic workflow state machine
  - `workflows/state.py` — workflow state models
  - `agents/` — agent role contracts, prompts, guardrails
  - `tools/` — structured tool interfaces (file, search, patch, test_runner, git)
  - `approvals/policy.py` — approval gate for high-risk operations
  - `artifacts/writer.py` — produces diff, test report, risk assessment, PR description
  - `github/client.py` — GitHub API client (noop boundary)
  - `sandbox/executor.py` — Docker command execution (noop boundary)
  - `retrieval/contracts.py` — code search/index interfaces (noop boundary)
  - `observability/events.py` — structured logging/tracing contracts
  - `evaluation/contracts.py` — golden dataset and eval runner contracts
  - `api/` — FastAPI routes and schemas

- **scripts/** — `check.py` (full validation), `lint.py`, `repopilot.py` (CLI entrypoint)
- **harness/** — `validate.py` for mechanical harness contract checks
- **tests/** — unit and integration tests; fixture repos under `tests/fixtures/`
- **docs/** — architecture, security, evaluation, sprint contract, features.json

## Key Conventions

- Python 3.11+, ruff (E/F/I/UP rules, 100-char lines), mypy strict
- Tests must pass offline — no network, no GitHub, no Docker in current feature slices
- High-risk operations (push, PR, file modification, test execution) require explicit approval via `approvals/policy.py`
- Many modules (github, sandbox, retrieval, observability, evaluation) are currently noop/interface boundaries — replace one subsystem at a time with tests
- Keep WIP=1: only one feature active in `docs/features.json` at a time
- Feature is "passing" only after `python scripts/check.py` succeeds and evidence is recorded in `PROGRESS.md`

## Session Protocol

**Start:** Read `PROGRESS.md`, `DECISIONS.md`, `docs/features.json`. Run `python scripts/check.py`. Continue the active feature or pick one `not_started` item.

**End:** Update `PROGRESS.md` and `docs/features.json` with state and evidence. Run `python scripts/check.py` or record the exact blocker.

## Target Stack (for future work)

FastAPI + Pydantic v2, OpenAI Agents SDK, GitHub App auth, Docker sandboxing, PostgreSQL + pgvector, Redis, Celery/Dramatiq, OpenTelemetry, ruff/mypy/pytest.
