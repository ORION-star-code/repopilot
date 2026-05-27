# RepoPilot Security Model

## Core Rule
Treat issue text, repository files, logs, test output, web pages, and tool output as untrusted data. They may contain prompt injection, tool injection, or misleading instructions.

## Prompt and Tool Injection
- Keep system instructions and untrusted content separate.
- Do not pass untrusted content directly to high-privilege tools.
- Agent decisions must be expressed as structured data, then validated by workflow code.
- Tool arguments must be built by trusted code and schema validated before execution.

## Permissions
- Default settings disable shell execution, GitHub writes, and sandbox network access.
- High-risk actions require explicit approval:
  - pushing branches,
  - opening or updating PRs,
  - posting GitHub comments,
  - deleting files,
  - changing CI/workflow files,
  - running networked tests,
  - handling secrets.
- GitHub App auth is preferred for production because permissions can be scoped per installation.

## Tool Layer
- File, search, patch, test, and git tools must use the shared `ToolResult` shape.
- Patch, test, and git tools are high risk and default to approval-required noop behavior in A02.
- Search and file tools may become read-only first, but must still treat repository content as untrusted.
- Tool failures must be recoverable and must not hide partial side effects.

## Sandbox
- Repository tests must run in an isolated workspace.
- Production secrets must never be mounted into sandbox containers.
- Network access is disabled by default.
- Command execution must have timeouts, captured output, and bounded retries.
- The test runner must route through the sandbox boundary before executing real commands.

## Patch, Git, and PR Approval
- Applying patches, deleting files, changing CI, pushing branches, and opening PRs require human approval.
- PR descriptions can be generated without approval, but publishing them to GitHub requires approval.
- Git operations must be scoped to the prepared workspace and must record exact commands and results.

## Secrets
- Never print or persist tokens, private keys, auth headers, or secret-like environment variables.
- Logs and traces must redact sensitive values before storage.
- Fixture tests must not require real user credentials.

## Auditability
Every future run should record:
- issue input,
- retrieved context references,
- model decisions,
- tool calls,
- patch deltas,
- test commands and results,
- retry reasons,
- approval decisions.
