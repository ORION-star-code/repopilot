import tempfile
import unittest
from pathlib import Path

from repopilot.issue_fetchers import FixtureIssueFetcher, IssueFixtureError, IssueIntakeError
from repopilot.issue_intake import normalize_issue_input

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "github_issues"


class IssueIntakeTest(unittest.TestCase):
    def test_github_issue_url_is_normalized(self):
        request = normalize_issue_input("https://github.com/octo/repo/issues/42")

        self.assertEqual(request.source, "github_issue")
        self.assertEqual(request.repository, "octo/repo")
        self.assertEqual(request.issue_number, 42)
        self.assertEqual(request.title, "octo/repo#42")
        self.assertEqual(request.labels, [])

    def test_bug_description_is_normalized(self):
        request = normalize_issue_input("Login fails after token refresh\nExpected retry.")

        self.assertEqual(request.source, "bug_description")
        self.assertEqual(request.title, "Login fails after token refresh")
        self.assertIn("Expected retry.", request.body)

    def test_empty_input_is_rejected(self):
        with self.assertRaises(IssueIntakeError):
            normalize_issue_input("   ")

    def test_github_issue_fixture_is_normalized(self):
        request = normalize_issue_input(
            "https://github.com/octo/repo/issues/42",
            issue_fetcher=FixtureIssueFetcher(FIXTURE_ROOT / "octo_repo_42.json"),
        )

        self.assertEqual(request.source, "github_issue_fixture")
        self.assertEqual(request.repository, "octo/repo")
        self.assertEqual(request.issue_number, 42)
        self.assertEqual(request.title, "Retry token refresh after transient auth failure")
        self.assertEqual(request.labels, ["bug", "auth"])
        self.assertEqual(request.author, "mona")
        self.assertEqual(request.created_at, "2026-05-20T10:00:00Z")
        self.assertEqual(request.updated_at, "2026-05-21T12:30:00Z")
        self.assertEqual(request.metadata["fetcher"], "FixtureIssueFetcher")

    def test_missing_fixture_is_recoverable(self):
        with self.assertRaisesRegex(IssueFixtureError, "does not exist"):
            normalize_issue_input(
                "https://github.com/octo/repo/issues/42",
                issue_fetcher=FixtureIssueFetcher(FIXTURE_ROOT / "missing.json"),
            )

    def test_malformed_fixture_is_recoverable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "bad.json"
            fixture.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(IssueFixtureError, "not valid JSON"):
                normalize_issue_input(
                    "https://github.com/octo/repo/issues/42",
                    issue_fetcher=FixtureIssueFetcher(fixture),
                )

    def test_fixture_must_match_input_url(self):
        with self.assertRaisesRegex(IssueFixtureError, "does not match input URL"):
            normalize_issue_input(
                "https://github.com/octo/repo/issues/99",
                issue_fetcher=FixtureIssueFetcher(FIXTURE_ROOT / "octo_repo_42.json"),
            )


if __name__ == "__main__":
    unittest.main()
