# RepoPilot Code Review Standards

## Patch Philosophy
RepoPilot should produce small, reviewable patches. Prefer the narrowest change that fixes the failing behavior and preserves existing architecture.

## Required PR Evidence
Every future PR description should include:
- problem summary,
- root cause hypothesis,
- files changed,
- test commands run,
- test result summary,
- risk assessment,
- rollback notes when relevant.

## Review Checklist
- Does the patch address the issue rather than unrelated cleanup?
- Are tool calls and model decisions traceable?
- Are tests focused and meaningful?
- Did the workflow avoid broad permissions?
- Is any high-risk operation approved?
- Is untrusted input kept separate from instructions?

## Rejection Signals
- Large unrelated rewrites.
- No test evidence.
- Hidden network or credential dependency.
- Unbounded retry behavior.
- Agent-generated claims not supported by code, tests, or logs.
