"""Tests for run manager module."""

from __future__ import annotations

from datetime import UTC, datetime

from repopilot.runs.manager import RunManager, RunRecord, RunStatus


class TestRunStatus:
    """Test RunStatus enum."""

    def test_enum_values(self) -> None:
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.WAITING_FOR_APPROVAL == "waiting_for_approval"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.SUCCEEDED == "succeeded"
        assert RunStatus.CANCELED == "canceled"
        assert len(list(RunStatus)) == 6


class TestRunRecord:
    """Test RunRecord model."""

    def test_record_creation(self) -> None:
        now = datetime.now(UTC)
        record = RunRecord(
            run_id="run_1",
            issue_input="test issue",
            repository="owner/repo",
            created_at=now,
            updated_at=now,
        )
        assert record.run_id == "run_1"
        assert record.issue_input == "test issue"
        assert record.repository == "owner/repo"
        assert record.status == RunStatus.PENDING
        assert record.approval_required is False
        assert record.approved is False
        assert record.artifact_refs == []

    def test_record_defaults(self) -> None:
        now = datetime.now(UTC)
        record = RunRecord(
            run_id="run_1",
            issue_input="test",
            created_at=now,
            updated_at=now,
        )
        assert record.repository is None
        assert record.status == RunStatus.PENDING


class TestRunManager:
    """Test RunManager in-memory operations."""

    def test_start_run(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue", repository="owner/repo")

        assert record.run_id.startswith("run_")
        assert record.issue_input == "test issue"
        assert record.repository == "owner/repo"
        assert record.status == RunStatus.PENDING

    def test_start_run_without_repository(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")

        assert record.repository is None

    def test_get_run(self) -> None:
        manager = RunManager()
        created = manager.start_run("test issue")

        retrieved = manager.get_run(created.run_id)
        assert retrieved.run_id == created.run_id
        assert retrieved.issue_input == "test issue"

    def test_get_run_unknown_id_raises(self) -> None:
        manager = RunManager()

        try:
            manager.get_run("nonexistent")
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_update_status_valid_transition(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")

        updated = manager.update_status(record.run_id, RunStatus.RUNNING)
        assert updated.status == RunStatus.RUNNING
        assert updated.updated_at >= record.created_at

    def test_update_status_pending_to_canceled(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")

        updated = manager.update_status(record.run_id, RunStatus.CANCELED)
        assert updated.status == RunStatus.CANCELED

    def test_update_status_invalid_transition_raises(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")

        try:
            manager.update_status(record.run_id, RunStatus.SUCCEEDED)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_update_status_terminal_state_raises(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")
        manager.update_status(record.run_id, RunStatus.RUNNING)
        manager.update_status(record.run_id, RunStatus.SUCCEEDED)

        try:
            manager.update_status(record.run_id, RunStatus.RUNNING)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_update_status_unknown_id_raises(self) -> None:
        manager = RunManager()

        try:
            manager.update_status("nonexistent", RunStatus.RUNNING)
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_list_runs(self) -> None:
        manager = RunManager()
        manager.start_run("issue 1")
        manager.start_run("issue 2")
        manager.start_run("issue 3")

        runs = manager.list_runs()
        assert len(runs) == 3
        assert all(isinstance(r, RunRecord) for r in runs)

    def test_list_runs_empty(self) -> None:
        manager = RunManager()
        assert manager.list_runs() == []

    def test_custom_id_factory(self) -> None:
        counter = [0]
        def custom_id() -> str:
            counter[0] += 1
            return f"custom-{counter[0]}"

        manager = RunManager(id_factory=custom_id)
        record = manager.start_run("test")
        assert record.run_id == "custom-1"

    def test_custom_clock(self) -> None:
        fixed_time = datetime(2026, 1, 1, tzinfo=UTC)
        manager = RunManager(clock=lambda: fixed_time)

        record = manager.start_run("test")
        assert record.created_at == fixed_time
        assert record.updated_at == fixed_time

    def test_full_lifecycle(self) -> None:
        manager = RunManager()
        record = manager.start_run("test issue")
        assert record.status == RunStatus.PENDING

        running = manager.update_status(record.run_id, RunStatus.RUNNING)
        assert running.status == RunStatus.RUNNING

        waiting = manager.update_status(record.run_id, RunStatus.WAITING_FOR_APPROVAL)
        assert waiting.status == RunStatus.WAITING_FOR_APPROVAL

        running_again = manager.update_status(record.run_id, RunStatus.RUNNING)
        assert running_again.status == RunStatus.RUNNING

        succeeded = manager.update_status(record.run_id, RunStatus.SUCCEEDED)
        assert succeeded.status == RunStatus.SUCCEEDED
