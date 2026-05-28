"""Structured events for future logs and traces."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TraceEventType(StrEnum):
    WORKFLOW = "workflow"
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"
    TEST_RUN = "test_run"
    APPROVAL = "approval"
    STAGE_TRANSITION = "stage_transition"
    RETRY = "retry"
    ERROR = "error"
    ARTIFACT_WRITE = "artifact_write"
    SANDBOX_EXECUTION = "sandbox_execution"


class TraceSeverity(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TraceEvent(BaseModel):
    """Structured trace event for one repair run."""

    run_id: str
    event_type: TraceEventType
    message: str
    severity: TraceSeverity = TraceSeverity.INFO
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraceCollector:
    """In-memory trace event collector."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(self, event: TraceEvent) -> None:
        """Add an event to the collection."""
        self._events.append(event)

    def events(self) -> list[TraceEvent]:
        """Return a copy of collected events."""
        return list(self._events)

    def events_for_run(self, run_id: str) -> list[TraceEvent]:
        """Return events for a specific run."""
        return [e for e in self._events if e.run_id == run_id]

    def clear(self) -> None:
        """Clear all collected events."""
        self._events.clear()

    @property
    def count(self) -> int:
        """Return the number of collected events."""
        return len(self._events)

    def export_json(self) -> str:
        """Export all events as a JSON array string."""
        return json.dumps([e.model_dump(mode="json") for e in self._events], indent=2)

    def export_jsonl(self, path: Path) -> None:
        """Append events to a JSONL file (one JSON object per line)."""
        with open(path, "a", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(event.model_dump(mode="json")) + "\n")
