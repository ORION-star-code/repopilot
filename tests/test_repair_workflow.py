import unittest

from repopilot.issue_intake import normalize_issue_input
from repopilot.models import RepoSnapshot
from repopilot.repair_workflow import create_repair_plan, empty_artifacts, run_dry_repair_workflow


class RepairWorkflowTest(unittest.TestCase):
    def test_repair_plan_contains_expected_validation_command(self):
        request = normalize_issue_input("Tests fail when config is missing")
        snapshot = RepoSnapshot(root="/repo", files=["src/app.py", "tests/test_app.py"])

        plan = create_repair_plan(request, snapshot)

        self.assertEqual(plan.target_files, ["src/app.py", "tests/test_app.py"])
        self.assertIn("python scripts/check.py", plan.verification)
        self.assertTrue(any("Emit dry-run diff" in step for step in plan.steps))

    def test_empty_artifacts_express_pr_output_contract(self):
        artifacts = empty_artifacts()

        self.assertEqual(artifacts.git_diff, "")
        self.assertEqual(artifacts.test_report, "")
        self.assertEqual(artifacts.risk_assessment, "")
        self.assertEqual(artifacts.pr_description, "")

    def test_dry_run_workflow_emits_noop_repair_artifacts(self):
        request = normalize_issue_input("Token refresh fails after transient provider errors")
        snapshot = RepoSnapshot(
            root="/repo",
            files=["src/auth.py", "tests/test_auth.py"],
            important_files=["src/auth.py", "tests/test_auth.py"],
        )

        result = run_dry_repair_workflow(request, snapshot)

        self.assertEqual(result.workflow_status, "dry_run_completed")
        self.assertEqual(result.retry_count, 0)
        self.assertEqual(result.max_retries, 2)
        self.assertTrue(result.approval_required)
        self.assertEqual(result.plan.target_files, ["src/auth.py", "tests/test_auth.py"])
        self.assertEqual(result.artifacts.git_diff, "Dry run only. No files were modified.")
        self.assertIn("No tests were executed", result.artifacts.test_report)
        self.assertIn("No code was changed", result.artifacts.pr_description)
        self.assertIn("Low execution risk", result.artifacts.risk_assessment)


if __name__ == "__main__":
    unittest.main()
