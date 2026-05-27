"""Evaluation data contracts for golden repair datasets."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluationMetric(StrEnum):
    TASK_SUCCESS_RATE = "task_success_rate"
    TOOL_CALL_ACCURACY = "tool_call_accuracy"
    PATCH_CORRECTNESS = "patch_correctness"
    TEST_PASS_RATE = "test_pass_rate"
    SECURITY_VIOLATION_RATE = "security_violation_rate"
    RETRY_SUCCESS_RATE = "retry_success_rate"
    RETRIEVAL_HIT_RATE = "retrieval_hit_rate"
    REPAIR_TIME = "repair_time"
    RETRY_COUNT = "retry_count"


class GoldenCase(BaseModel):
    """One issue-to-repair evaluation case."""

    case_id: str
    issue_input: str
    repository_fixture: str
    expected_files: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    expected_diff: str = ""
    expected_test_pass: bool = True
    timeout_seconds: int = 300
    known_failure_signal: str = ""
    reviewer_notes: str = ""


class EvaluationResult(BaseModel):
    """Result of running an evaluation case."""

    case_id: str
    passed: bool
    metrics: dict[EvaluationMetric, float] = Field(default_factory=dict)
    notes: str = ""
    actual_diff: str = ""
    actual_test_output: str = ""
