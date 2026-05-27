# Quality Notes

## RepoPilot Bootstrap (Quality: C)
- Verification passed: 2026-05-23, `python scripts/check.py`
- Agent understandable: yes
- Test stability: smoke tests are offline and deterministic
- Architecture boundaries: initial package split for intake, repo analysis, planning, and workflow artifacts
- Code conventions: standard-library-first Python, small pure functions, dataclass contracts

## A01 Architecture Skeleton (Quality: B-)
- Verification passed: 2026-05-23, `python scripts/check.py`
- Agent understandable: yes, with explicit module boundaries and architecture docs
- Test stability: pytest coverage is offline and deterministic
- Architecture boundaries: API, workflows, agents, tools, GitHub, sandbox, retrieval, observability, and evaluation are separated
- External side effects: disabled by default; GitHub and sandbox are noop/interface-only

## F01 Issue Intake (Quality: B)
- Verification passed: 2026-05-23, `python scripts/check.py`
- Scope: GitHub Issue URL parsing, raw bug descriptions, fixture-backed GitHub issue loading
- Test stability: offline fixture tests, no network or token dependency
- Safety boundary: issue content remains data only; no shell, GitHub, or repository side effects

## A02 Layered Architecture Alignment (Quality: B-)
- Verification passed: 2026-05-23, `python scripts/check.py`
- Scope: run manager, workspace manager, workflow orchestrator, agent roles, tool categories, artifact bundle, and layered architecture docs
- Test stability: offline contract tests only
- Safety boundary: all new side-effectful layers are noop or approval-required

## F02 Repository Analysis and Retrieval (Quality: B)
- Verification passed: 2026-05-23, `python scripts/check.py`
- Scope: read-only repository snapshot, file classification, important file selection, and deterministic local text retrieval
- Test stability: fixture repository tests with ignored `.git` and `node_modules`
- Safety boundary: no repository writes, shell commands, git, network, or live sandbox execution

## F03 Dry-Run Repair Workflow (Quality: B)
- Verification passed: 2026-05-24, `python scripts/check.py`
- Scope: deterministic repair plan, dry-run artifacts, bounded retry metadata, approval-required workflow status
- Test stability: offline tests with no patch, shell, git, network, or sandbox execution
- Safety boundary: emits noop diff/test report/risk/PR description only

## F04 Approval-Gated Patch/Test Boundaries (Quality: B)
- Verification passed: 2026-05-24, `python scripts/check.py`
- Scope: approval policy, patch proposal schema, test execution request schema, noop patch/test tools
- Test stability: offline unit tests only
- Safety boundary: tools validate requests and require approval, but still do not patch files or execute commands

## Cleanup Priorities
1. Add sandbox execution planning before enabling any real test command execution.
2. Add transition tests when workflow stages begin advancing beyond static contracts.
3. Replace noop tool boundaries incrementally only after read-only tests exist.
