"""Tests for observability trace event collection."""

from __future__ import annotations

from repopilot.observability import (
    TraceCollector,
    TraceEvent,
    TraceEventType,
    TraceSeverity,
)


class TestTraceEvent:
    """Test TraceEvent model construction."""

    def test_minimal_event(self) -> None:
        event = TraceEvent(
            run_id="run_1",
            event_type=TraceEventType.WORKFLOW,
            message="started",
        )
        assert event.run_id == "run_1"
        assert event.event_type == TraceEventType.WORKFLOW
        assert event.severity == TraceSeverity.INFO
        assert event.metadata == {}

    def test_event_with_severity(self) -> None:
        event = TraceEvent(
            run_id="run_1",
            event_type=TraceEventType.ERROR,
            message="something broke",
            severity=TraceSeverity.ERROR,
        )
        assert event.severity == TraceSeverity.ERROR

    def test_event_with_metadata(self) -> None:
        event = TraceEvent(
            run_id="run_1",
            event_type=TraceEventType.TOOL_CALL,
            message="called tool",
            metadata={"tool": "file", "action": "read"},
        )
        assert event.metadata["tool"] == "file"


class TestTraceCollector:
    """Test TraceCollector in-memory collection."""

    def test_record_and_retrieve(self) -> None:
        collector = TraceCollector()
        event = TraceEvent(
            run_id="run_1",
            event_type=TraceEventType.WORKFLOW,
            message="test",
        )
        collector.record(event)
        assert len(collector.events()) == 1
        assert collector.events()[0].message == "test"

    def test_events_returns_copy(self) -> None:
        collector = TraceCollector()
        collector.record(TraceEvent(
            run_id="run_1",
            event_type=TraceEventType.WORKFLOW,
            message="test",
        ))
        events = collector.events()
        events.clear()
        assert len(collector.events()) == 1

    def test_events_for_run_filters_correctly(self) -> None:
        collector = TraceCollector()
        collector.record(TraceEvent(
            run_id="run_1", event_type=TraceEventType.WORKFLOW, message="a",
        ))
        collector.record(TraceEvent(
            run_id="run_2", event_type=TraceEventType.WORKFLOW, message="b",
        ))
        collector.record(TraceEvent(
            run_id="run_1", event_type=TraceEventType.TOOL_CALL, message="c",
        ))
        run1_events = collector.events_for_run("run_1")
        assert len(run1_events) == 2
        assert all(e.run_id == "run_1" for e in run1_events)

    def test_events_for_run_returns_empty_for_unknown(self) -> None:
        collector = TraceCollector()
        assert collector.events_for_run("nonexistent") == []

    def test_clear_removes_all_events(self) -> None:
        collector = TraceCollector()
        collector.record(TraceEvent(
            run_id="run_1", event_type=TraceEventType.WORKFLOW, message="test",
        ))
        collector.clear()
        assert collector.events() == []

    def test_empty_collector_returns_empty_list(self) -> None:
        collector = TraceCollector()
        assert collector.events() == []


class TestTraceEventType:
    """Test TraceEventType enum completeness."""

    def test_expected_event_types_exist(self) -> None:
        expected = {
            "workflow", "tool_call", "model_call", "test_run",
            "approval", "stage_transition", "retry", "error",
        }
        assert {e.value for e in TraceEventType} == expected


class TestTraceSeverity:
    """Test TraceSeverity enum completeness."""

    def test_expected_severities_exist(self) -> None:
        assert {s.value for s in TraceSeverity} == {"debug", "info", "warning", "error"}
