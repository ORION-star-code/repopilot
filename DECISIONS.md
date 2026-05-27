# Design Decisions

## 2026-05-23: Create a harness-first scaffold
- Decision: Initialize RepoPilot with an agent-ready harness before feature work.
- Reason: Fresh agent sessions need durable context, validation commands, progress state, and task boundaries.
- Rejected alternatives: Start coding features from an empty directory without a documented bootstrap contract.
- Constraints: Keep WIP=1, define executable completion evidence, and keep project knowledge in versioned files.

## 2026-05-23: Initial stack
- Decision: Python 3.11+, Standard-library-first CLI package, unittest smoke tests, optional GitHub/tool integrations later
- Reason: RepoPilot is an automation agent whose first durable value is command orchestration, repository inspection, and artifact generation. A small Python CLI keeps the bootstrap runnable on a clean checkout before committing to web services, queues, databases, or hosted workers.
- Rejected alternatives: FastAPI plus database as the first scaffold, Node.js CLI, or a notebook-first prototype.
- Constraints: Setup, dev, test, lint, and check commands must remain accurate.

## 2026-05-23: Keep external integrations behind narrow interfaces
- Decision: Start with local parsing, repository inspection, planning contracts, and CLI wrappers; add GitHub API clients, model providers, sandboxed edit tools, and PR publishing behind explicit modules later.
- Reason: The project needs reliable retry and validation loops. Narrow interfaces make it easier to test those loops without network credentials or live repositories.
- Rejected alternatives: Hard-code GitHub, LLM, and git side effects into one script.
- Constraints: Smoke tests should run offline, and future integrations must preserve `python scripts/check.py` as the baseline validation path.

## 2026-05-23: Adopt production-oriented target stack in AGENTS.md
- Decision: Expand `AGENTS.md` to document the production target stack: FastAPI, Pydantic v2, OpenAI Agents SDK, GitHub App auth, Docker sandboxing, PostgreSQL/pgvector, Redis, background jobs, observability, and evaluation.
- Reason: RepoPilot is intended to modify code and interact with GitHub, so future agents need explicit safety, permission, testability, and traceability constraints before adding business features.
- Rejected alternatives: Keep `AGENTS.md` as a minimal bootstrap note or add large frameworks without a clear need.
- Constraints: The current checkout remains a bootstrap skeleton; dependencies should be introduced incrementally with tests and passing validation.

## 2026-05-23: Create architecture skeleton before feature development
- Decision: Add an A01 architecture slice with CLI/API entrypoints, module boundaries, safety defaults, architecture docs, and validation before continuing F01.
- Reason: RepoPilot needs stable interfaces for agents, tools, GitHub, sandboxing, retrieval, observability, and evaluation before concrete repair features are implemented.
- Rejected alternatives: Continue directly into F01 issue fetching, or add the full production platform with database, queue, Docker, and live OpenAI/GitHub integrations immediately.
- Constraints: A01 must avoid real external side effects and must pass `python scripts/check.py`.

## 2026-05-23: Keep F01 GitHub intake fixture-backed
- Decision: Implement issue intake with URL parsing, raw bug descriptions, and local JSON fixture loading rather than live GitHub API access.
- Reason: F01 needs stable, offline regression tests and a clear fetcher boundary before adding token-backed or GitHub App clients.
- Rejected alternatives: Depend on `gh` CLI login state or call GitHub REST directly during tests.
- Constraints: Fixture-backed intake must not perform network, shell, repository, or GitHub write side effects.

## 2026-05-23: Align architecture to layered run workflow
- Decision: Add an A02 architecture slice for Run Manager, Workspace Manager, Repair Workflow Orchestrator, Agent Reasoning Layer, Tool Layer, Artifacts Writer, Observability, and Evaluation boundaries.
- Reason: The project needs explicit production flow boundaries before building repository analysis and repair execution features.
- Rejected alternatives: Fold the architecture work into F02 or only update documentation without code contracts.
- Constraints: A02 must remain contract/noop only and must not execute real GitHub, Docker, git, shell, LLM, or patch side effects.

## 2026-05-23: Keep F02 repository context read-only and deterministic
- Decision: Implement repository analysis and local retrieval with filesystem reads over fixture/local repositories only.
- Reason: Planning needs reliable context before any patch/test/git side effects are introduced.
- Rejected alternatives: Start with embeddings, tree-sitter, ripgrep subprocesses, or live cloned repositories.
- Constraints: F02 must not modify files, execute commands, access network, or require external services.

## 2026-05-24: Implement F03 as dry-run workflow before patch execution
- Decision: Produce repair plan and artifacts without applying patches, running tests, or invoking git.
- Reason: RepoPilot needs a reviewable workflow output contract before any write-side or command-execution capability is added.
- Rejected alternatives: Apply patches directly, execute local tests, or call sandbox/git tools before approval boundaries are explicit.
- Constraints: F03 artifacts must clearly state that no code changed and no tests executed.

## 2026-05-24: Add approval gates before patch or test execution
- Decision: Add strict approval policy and structured patch/test request models while keeping patch and test tools noop.
- Reason: RepoPilot must validate high-risk operation requests and require explicit approval before any future executor can run them.
- Rejected alternatives: Let tools accept arbitrary dictionaries, or execute approved requests before sandbox planning exists.
- Constraints: F04 tools must not modify files, run commands, access network, or call git.

## 2026-05-27: Introduce ExecutionMode enum for sandbox execution planning
- Decision: Add ExecutionMode (DRY_RUN/APPROVED) to models.py and wire through sandbox executor, tools, and config.
- Reason: The system needs to distinguish between dry-run planning (simulate without executing) and approved execution (attempt real sandbox run). This enables reviewable command plans before any real side effects.
- Rejected alternatives: Keep tools as pure noop without execution mode branching; add execution mode only to tools without sandbox awareness.
- Constraints: Default to APPROVED everywhere for F04 backward compatibility. Use `Any` type for CommandPlan.request to avoid circular import with sandbox/executor. No real command execution is added — sandbox remains noop in APPROVED mode.

## 2026-05-27: Replace NoopSandboxExecutor with subprocess-based execution
- Decision: Add SubprocessSandboxExecutor using subprocess.run with timeout, output capture, and error handling. Wire it into test_runner tool for APPROVED mode.
- Reason: F05 established execution modes but APPROVED mode still refused. The project needs actual command execution to run tests and validate patches.
- Rejected alternatives: Docker-based execution (too heavy for current stage), shell=True (security risk), streaming output (unnecessary complexity).
- Constraints: No shell=True (list[str] commands only), timeout enforced via subprocess.run(timeout=), network isolation deferred to future Docker executor, NoopSandboxExecutor kept for tests that don't need real execution.

## 2026-05-27: Implement real tool backends (F07-F10)
- Decision: Replace all noop tools with real implementations: RealFileTool (read/write/list), RealSearchTool (keyword+grep), RealPatchTool (subprocess patch), RealGitTool (subprocess git).
- Reason: The end-to-end goal requires tools that actually perform file I/O, code search, patch application, and git operations.
- Rejected alternatives: Keep noop tools and add separate real implementations (would double the surface area); use third-party libraries (adds dependencies for simple operations).
- Constraints: All tools keep approval gates for write operations. No shell=True anywhere. Timeout on all subprocess calls. Backward-compatible aliases (NoopXTool = RealXTool) for existing tests.

## 2026-05-27: Real repair orchestrator with retry loop (F11-F12)
- Decision: Implement RealRepairWorkflowOrchestrator that drives INTAKE→ANALYZE→RETRIEVE→PLAN→PATCH→TEST→REPORT with real tool calls and a TEST+REFLECT retry loop.
- Reason: The project needs a working end-to-end pipeline, not just individual tools.
- Rejected alternatives: LLM-based orchestrator (requires API key, not offline-testable); separate retry module (simpler to keep in orchestrator).
- Constraints: Deterministic for offline testing. Validation command is configurable. Max retries from config. No LLM integration yet — patch generation is a placeholder.

## 2026-05-27: CLI run subcommand (F14)
- Decision: Add `repopilot run` CLI command that drives the full repair workflow and optionally saves artifacts to disk.
- Reason: Users need a single command to run the complete repair pipeline.
- Rejected alternatives: API-only (requires server); interactive TUI (over-engineered for current stage).
- Constraints: Accepts issue input, repo path, diff file, test command, max retries, output directory. Returns exit code 0 on success, 1 on failure.
