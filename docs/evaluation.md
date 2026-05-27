# RepoPilot Evaluation

## Principle
An agent capability is not production-grade until it is evaluated. Prompt quality alone is not a release criterion.

## Golden Dataset
Each golden case should include:
- issue input,
- repository fixture,
- expected touched files,
- required tests,
- known failure signal,
- acceptable patch behavior,
- reviewer notes.

## Metrics
Track at least:
- task success rate,
- tool-call accuracy,
- patch correctness,
- test pass rate,
- retry success rate,
- retrieval hit rate,
- unsupported-claim rate,
- security violation rate,
- cost and latency.

## Evaluation Layers
1. Unit tests for parsing, schemas, tools, and state transitions.
2. Integration tests for API, CLI, workflow orchestration, and sandbox boundaries.
3. Golden dataset regression runs for issue-to-patch behavior.
4. LLM-as-judge checks for plan quality and PR description quality.
5. Human review for release gates and high-risk changes.

LLM-as-judge must never be the only evaluator for correctness or security.

## A01 Coverage
A01 only creates evaluation contracts and verifies that they are importable. Actual golden datasets and eval runners are future work.
