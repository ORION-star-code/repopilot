# Sprint Contract: A02 Layered Architecture Alignment

## Scope
- Align RepoPilot with the layered run manager -> workflow -> workspace/retrieval/agent/tool/artifact architecture.
- Add run manager, workspace manager, artifact writer, and noop workflow orchestrator contracts.
- Expand agent roles and tool categories to match triage/planner/patch/failure/reviewer and file/search/patch/test/git.
- Update architecture/security docs and Harness state for A02.

## Verification Standards
- `python harness/validate.py` passes.
- `python scripts/check.py` passes, or blockers are written in `PROGRESS.md`.
- A fresh agent can answer how to run, how to test, and what to do next from repository files alone.

## Exclusions
- Real GitHub App authentication.
- Database, Redis, queue, vector index, or Docker execution.
- OpenAI Agents SDK calls.
- Real file modification, test execution, git operations, PR creation, or GitHub comments.
