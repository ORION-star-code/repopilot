"""Tests for evaluation data contracts."""

from __future__ import annotations

from repopilot.evaluation.contracts import (
    EvaluationMetric,
    EvaluationResult,
    GoldenCase,
)


class TestGoldenCase:
    """Test GoldenCase model construction."""

    def test_minimal_case(self) -> None:
        case = GoldenCase(
            case_id="case_001",
            issue_input="Fix the login bug",
            repository_fixture="fixtures/repo_001",
        )
        assert case.case_id == "case_001"
        assert case.expected_files == []
        assert case.required_tests == []
        assert case.expected_diff == ""
        assert case.expected_test_pass is True
        assert case.timeout_seconds == 300

    def test_case_with_all_fields(self) -> None:
        case = GoldenCase(
            case_id="case_002",
            issue_input="Auth fails",
            repository_fixture="fixtures/auth_repo",
            expected_files=["src/auth.py"],
            required_tests=["test_auth.py"],
            expected_diff="diff --git a/src/auth.py",
            expected_test_pass=True,
            timeout_seconds=600,
            known_failure_signal="AssertionError",
            reviewer_notes="Regression from v2.1",
        )
        assert case.expected_files == ["src/auth.py"]
        assert case.timeout_seconds == 600
        assert case.known_failure_signal == "AssertionError"


class TestEvaluationResult:
    """Test EvaluationResult model construction."""

    def test_minimal_result(self) -> None:
        result = EvaluationResult(
            case_id="case_001",
            passed=True,
        )
        assert result.passed is True
        assert result.metrics == {}
        assert result.notes == ""

    def test_result_with_metrics(self) -> None:
        result = EvaluationResult(
            case_id="case_001",
            passed=True,
            metrics={
                EvaluationMetric.TASK_SUCCESS_RATE: 1.0,
                EvaluationMetric.PATCH_CORRECTNESS: 0.95,
                EvaluationMetric.RETRY_COUNT: 1.0,
            },
        )
        assert result.metrics[EvaluationMetric.TASK_SUCCESS_RATE] == 1.0
        assert result.metrics[EvaluationMetric.RETRY_COUNT] == 1.0

    def test_failed_result(self) -> None:
        result = EvaluationResult(
            case_id="case_001",
            passed=False,
            notes="Patch did not fix the issue",
            actual_diff="diff --git a/wrong.py",
            actual_test_output="FAILED test_something",
        )
        assert result.passed is False
        assert "FAILED" in result.actual_test_output


class TestEvaluationMetric:
    """Test EvaluationMetric enum completeness."""

    def test_expected_metrics_exist(self) -> None:
        expected = {
            "task_success_rate",
            "tool_call_accuracy",
            "patch_correctness",
            "test_pass_rate",
            "security_violation_rate",
            "retry_success_rate",
            "retrieval_hit_rate",
            "repair_time",
            "retry_count",
        }
        assert {m.value for m in EvaluationMetric} == expected
