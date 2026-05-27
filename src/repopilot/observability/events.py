"""Structured events for future logs and traces."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TraceEventType(StrEnum):
    WORKFLOW = "workflow"
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"
    TEST_RUN = "test_run"
    APPROVAL = "approval"


class TraceEvent(BaseModel):
    """Structured trace event for one repair run."""

    run_id: str
    event_type: TraceEventType
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
