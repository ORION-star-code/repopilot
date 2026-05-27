"""Shared tool protocol and result shape."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol, Self

from pydantic import BaseModel


class ToolErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    APPROVAL_REQUIRED = "approval_required"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ToolCategory(StrEnum):
    """High-level tool subsystem categories."""

    FILE = "file"
    SEARCH = "search"
    PATCH = "patch"
    TEST = "test"
    GIT = "git"


class ToolResult(BaseModel):
    """Uniform structured result for all tool calls."""

    ok: bool
    data: Any | None = None
    error_code: ToolErrorCode | None = None
    message: str = ""
    approval_required: bool = False

    @classmethod
    def success(cls, data: Any | None = None, message: str = "") -> Self:
        return cls(ok=True, data=data, message=message)

    @classmethod
    def failure(cls, error_code: ToolErrorCode, message: str) -> Self:
        return cls(ok=False, error_code=error_code, message=message)

    @classmethod
    def requires_approval(cls, message: str) -> Self:
        return cls(
            ok=False,
            error_code=ToolErrorCode.APPROVAL_REQUIRED,
            message=message,
            approval_required=True,
        )


class Tool(Protocol):
    """Minimal protocol for agent-callable tools."""

    name: str
    category: ToolCategory
    approval_required: bool

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        """Execute the tool with structured arguments."""
