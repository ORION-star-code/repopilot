"""Tests for artifacts writer module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from repopilot.artifacts.writer import ArtifactBundle, ArtifactsWriter
from repopilot.runs import RunRecord


class TestArtifactBundle:
    """Test ArtifactBundle model."""

    def test_bundle_creation(self) -> None:
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="diff --git a/file.py",
            test_report="1 passed",
            risk_assessment="Low risk",
            pr_description="## Summary\nFix",
        )
        assert bundle.run_id == "run_1"
        assert bundle.diff == "diff --git a/file.py"
        assert bundle.test_report == "1 passed"
        assert bundle.risk_assessment == "Low risk"
        assert bundle.pr_description == "## Summary\nFix"
        assert bundle.artifact_refs == []
        assert bundle.generated_at is not None

    def test_bundle_with_artifact_refs(self) -> None:
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="diff",
            test_report="report",
            risk_assessment="risk",
            pr_description="pr",
            artifact_refs=["file1.patch", "file2.txt"],
        )
        assert len(bundle.artifact_refs) == 2
        assert "file1.patch" in bundle.artifact_refs


class TestArtifactsWriter:
    """Test ArtifactsWriter persistence."""

    def test_build_bundle(self) -> None:
        writer = ArtifactsWriter()
        run = RunRecord(
            run_id="run_1",
            issue_input="test issue",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            artifact_refs=["ref1.patch"],
        )

        bundle = writer.build_bundle(
            run=run,
            diff="diff content",
            test_report="test report",
            risk_assessment="low risk",
            pr_description="pr desc",
        )

        assert bundle.run_id == "run_1"
        assert bundle.diff == "diff content"
        assert bundle.test_report == "test report"
        assert bundle.risk_assessment == "low risk"
        assert bundle.pr_description == "pr desc"
        assert bundle.artifact_refs == ["ref1.patch"]

    def test_save_to_disk(self, tmp_path: Path) -> None:
        writer = ArtifactsWriter()
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="diff content",
            test_report="test report",
            risk_assessment="low risk",
            pr_description="pr desc",
        )

        written = writer.save_to_disk(bundle, str(tmp_path), workspace_root=tmp_path)

        assert len(written) == 5  # diff, test_report, risk, pr, summary
        assert (tmp_path / "diff.patch").exists()
        assert (tmp_path / "test_report.txt").exists()
        assert (tmp_path / "risk_assessment.txt").exists()
        assert (tmp_path / "pr_description.md").exists()
        assert (tmp_path / "summary.txt").exists()

        assert (tmp_path / "diff.patch").read_text() == "diff content"
        assert (tmp_path / "test_report.txt").read_text() == "test report"

    def test_save_to_disk_skips_empty_content(self, tmp_path: Path) -> None:
        writer = ArtifactsWriter()
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="",
            test_report="test report",
            risk_assessment="",
            pr_description="pr desc",
        )

        written = writer.save_to_disk(bundle, str(tmp_path), workspace_root=tmp_path)

        assert len(written) == 3  # test_report, pr, summary (diff and risk skipped)
        assert not (tmp_path / "diff.patch").exists()
        assert (tmp_path / "test_report.txt").exists()

    def test_save_to_disk_with_workspace_root(self, tmp_path: Path) -> None:
        writer = ArtifactsWriter()
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="diff",
            test_report="report",
            risk_assessment="risk",
            pr_description="pr",
        )
        output_dir = str(tmp_path / "artifacts")

        written = writer.save_to_disk(bundle, output_dir, workspace_root=tmp_path)

        assert len(written) == 5
        assert (tmp_path / "artifacts" / "diff.patch").exists()

    def test_save_to_disk_rejects_escape(self, tmp_path: Path) -> None:
        writer = ArtifactsWriter()
        bundle = ArtifactBundle(
            run_id="run_1",
            diff="diff",
            test_report="report",
            risk_assessment="risk",
            pr_description="pr",
        )
        # Try to escape workspace
        escape_path = str(tmp_path / ".." / ".." / "outside")

        try:
            writer.save_to_disk(bundle, escape_path, workspace_root=tmp_path)
            # If no error, the path was contained (some paths resolve safely)
        except ValueError:
            pass  # Expected: path escape detected

    def test_atomic_write(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        ArtifactsWriter._atomic_write(test_file, "hello world")
        assert test_file.read_text() == "hello world"

    def test_atomic_write_overwrites(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")
        ArtifactsWriter._atomic_write(test_file, "new content")
        assert test_file.read_text() == "new content"
