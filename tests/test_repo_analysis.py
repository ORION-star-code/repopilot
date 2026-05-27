import tempfile
import unittest
from pathlib import Path

from repopilot.repo_analysis import inspect_repository
from repopilot.retrieval import LocalCodeRetriever, RetrievalQuery

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "repos" / "python_service"


class RepoAnalysisTest(unittest.TestCase):
    def test_repository_snapshot_lists_code_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignored\n", encoding="utf-8")
            (root / "notes.bin").write_bytes(b"\x00\x01")

            snapshot = inspect_repository(root)

        self.assertEqual(snapshot.files, ["src/app.py"])
        self.assertEqual(snapshot.language_counts, {".py": 1})
        self.assertEqual(snapshot.test_files, [])
        self.assertEqual(snapshot.entrypoint_files, ["src/app.py"])

    def test_missing_repository_path_fails_clearly(self):
        with self.assertRaises(FileNotFoundError):
            inspect_repository("does-not-exist")

    def test_fixture_repository_snapshot_identifies_planning_context(self):
        snapshot = inspect_repository(FIXTURE_REPO)

        self.assertEqual(
            snapshot.files,
            [
                "pyproject.toml",
                "README.md",
                "src/app.py",
                "src/auth.py",
                "tests/auth_checks.py",
            ],
        )
        self.assertEqual(snapshot.language_counts, {".md": 1, ".py": 3, ".toml": 1})
        self.assertEqual(snapshot.config_files, ["pyproject.toml"])
        self.assertEqual(snapshot.entrypoint_files, ["src/app.py"])
        self.assertEqual(snapshot.test_files, ["tests/auth_checks.py"])
        self.assertNotIn("node_modules/ignored.js", snapshot.files)
        self.assertNotIn(".git/config", snapshot.files)

        detail_by_path = {detail.path: detail for detail in snapshot.file_details}
        self.assertEqual(detail_by_path["src/auth.py"].category, "source")
        self.assertGreater(detail_by_path["src/auth.py"].line_count, 0)
        self.assertIn("pyproject.toml", snapshot.important_files)
        self.assertIn("src/app.py", snapshot.important_files)

    def test_local_code_retriever_returns_ranked_snippets(self):
        results = LocalCodeRetriever().search(
            RetrievalQuery(
                repository_root=str(FIXTURE_REPO),
                text="refresh token",
                limit=2,
            )
        )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].source, "local_text")
        self.assertIn(results[0].path, {"src/auth.py", "tests/auth_checks.py", "src/app.py"})
        self.assertIn("refresh_token", results[0].snippet)


if __name__ == "__main__":
    unittest.main()
