"""Tests for workspace manager module."""

from __future__ import annotations

from pathlib import Path

from repopilot.runs import RunRecord
from repopilot.workspace import LocalWorkspaceManager, WorkspaceRef, WorkspaceSource


class TestWorkspaceSource:
    """Test WorkspaceSource enum."""

    def test_enum_values(self) -> None:
        assert WorkspaceSource.LOCAL == "local"
        assert WorkspaceSource.GITHUB_CLONE == "github_clone"
        assert WorkspaceSource.FIXTURE == "fixture"
        assert len(list(WorkspaceSource)) == 3


class TestWorkspaceRef:
    """Test WorkspaceRef model."""

    def test_minimal_ref(self) -> None:
        ref = WorkspaceRef(run_id="run_1", source=WorkspaceSource.LOCAL)
        assert ref.run_id == "run_1"
        assert ref.source == WorkspaceSource.LOCAL
        assert ref.path is None
        assert ref.repository is None
        assert ref.cloned is False
        assert ref.network_enabled is False

    def test_full_ref(self) -> None:
        ref = WorkspaceRef(
            run_id="run_1",
            source=WorkspaceSource.GITHUB_CLONE,
            path="/tmp/repo",
            repository="owner/repo",
            cloned=True,
            network_enabled=True,
        )
        assert ref.path == "/tmp/repo"
        assert ref.repository == "owner/repo"
        assert ref.cloned is True
        assert ref.network_enabled is True


class TestLocalWorkspaceManager:
    """Test LocalWorkspaceManager."""

    def test_prepare_workspace_without_root(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        manager = LocalWorkspaceManager()
        run = RunRecord(
            run_id="run_1",
            issue_input="test issue",
            repository="owner/repo",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        ref = manager.prepare_workspace(run)

        assert ref.run_id == "run_1"
        assert ref.source == WorkspaceSource.LOCAL
        assert ref.path is None
        assert ref.repository == "owner/repo"
        assert ref.cloned is False
        assert ref.network_enabled is False

    def test_prepare_workspace_with_root(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        manager = LocalWorkspaceManager(root=tmp_path)
        run = RunRecord(
            run_id="run_1",
            issue_input="test issue",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        ref = manager.prepare_workspace(run)

        assert ref.run_id == "run_1"
        assert ref.source == WorkspaceSource.LOCAL
        assert ref.path == str(tmp_path.resolve())
        assert ref.cloned is False
        assert ref.network_enabled is False

    def test_prepare_workspace_with_string_root(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        manager = LocalWorkspaceManager(root=str(tmp_path))
        run = RunRecord(
            run_id="run_1",
            issue_input="test issue",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        ref = manager.prepare_workspace(run)
        assert ref.path == str(tmp_path.resolve())
