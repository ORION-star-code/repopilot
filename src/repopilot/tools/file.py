"""File tool with real read, write, and list operations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy

from .contracts import ToolCategory, ToolErrorCode, ToolResult


class FileReadRequest(BaseModel):
    """Request to read a file."""

    path: str
    offset: int = 0
    limit: int = 0  # 0 means read all


class FileWriteRequest(BaseModel):
    """Request to write a file."""

    path: str
    content: str
    approved: bool = False


class FileListRequest(BaseModel):
    """Request to list directory contents."""

    path: str = "."
    recursive: bool = False


class RealFileTool:
    """File tool that reads, writes, and lists files."""

    name = "file"
    category = ToolCategory.FILE
    approval_required = False

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        action = arguments.get("action", "")
        if action == "read":
            return self._read(arguments)
        if action == "write":
            return self._write(arguments)
        if action == "list":
            return self._list(arguments)
        return ToolResult.failure(
            ToolErrorCode.INVALID_INPUT,
            f"Unknown action: {action}. Use 'read', 'write', or 'list'.",
        )

    def _read(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = FileReadRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        if not os.path.isfile(req.path):
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"File not found: {req.path}"
            )

        try:
            with open(req.path, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        if req.offset > 0:
            lines = lines[req.offset :]
        if req.limit > 0:
            lines = lines[: req.limit]

        content = "".join(lines)
        return ToolResult.success(
            data={"path": req.path, "content": content, "line_count": len(lines)},
            message=f"Read {len(lines)} lines from {req.path}",
        )

    def _write(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = FileWriteRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        decision = StrictApprovalPolicy().check(ApprovalSubject.PATCH, req.approved)
        if not decision.approved:
            return ToolResult.requires_approval(decision.reason)

        try:
            os.makedirs(os.path.dirname(req.path) or ".", exist_ok=True)
            with open(req.path, "w", encoding="utf-8") as f:
                f.write(req.content)
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        return ToolResult.success(
            data={"path": req.path, "bytes_written": len(req.content.encode())},
            message=f"Wrote {len(req.content)} chars to {req.path}",
        )

    def _list(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = FileListRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        if not os.path.isdir(req.path):
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Directory not found: {req.path}"
            )

        try:
            if req.recursive:
                entries = []
                for root, dirs, files in os.walk(req.path):
                    for name in files:
                        entries.append(os.path.join(root, name))
                    for name in dirs:
                        entries.append(os.path.join(root, name) + os.sep)
            else:
                entries = sorted(os.listdir(req.path))
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        return ToolResult.success(
            data={"path": req.path, "entries": entries, "count": len(entries)},
            message=f"Listed {len(entries)} entries in {req.path}",
        )


# Backward-compatible alias for tests that reference NoopFileTool.
NoopFileTool = RealFileTool
