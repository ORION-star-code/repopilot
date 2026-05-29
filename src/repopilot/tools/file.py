"""File tool with real read, write, and list operations."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from repopilot.approvals import ApprovalSubject, StrictApprovalPolicy

from .contracts import ToolCategory, ToolErrorCode, ToolResult
from .safety import contain_path

logger = logging.getLogger(__name__)

MAX_LIST_DEPTH = 10
MAX_LIST_ENTRIES = 10000
MAX_READ_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class FileReadRequest(BaseModel):
    """Request to read a file."""

    path: str = Field(min_length=1)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=0, ge=0)  # 0 means read all


class FileWriteRequest(BaseModel):
    """Request to write a file."""

    path: str = Field(min_length=1)
    content: str
    approved: bool = False


class FileListRequest(BaseModel):
    """Request to list directory contents."""

    path: str = Field(default=".", min_length=1)
    recursive: bool = False
    max_depth: int = Field(default=MAX_LIST_DEPTH, ge=1, le=100)
    max_entries: int = Field(default=MAX_LIST_ENTRIES, ge=1, le=100000)


class RealFileTool:
    """File tool that reads, writes, and lists files."""

    name = "file"
    category = ToolCategory.FILE
    approval_required = False

    def __init__(
        self,
        workspace_root: Path | None = None,
        policy: StrictApprovalPolicy | None = None,
    ) -> None:
        self._workspace_root = workspace_root or Path.cwd()
        self._policy = policy or StrictApprovalPolicy()

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

        try:
            resolved = contain_path(req.path, self._workspace_root)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.PERMISSION_DENIED, str(exc))

        if not resolved.is_file():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"File not found: {req.path}"
            )

        file_size = resolved.stat().st_size
        if file_size > MAX_READ_SIZE_BYTES:
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT,
                f"File too large ({file_size} bytes, limit {MAX_READ_SIZE_BYTES})",
            )

        try:
            with open(resolved, encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT, "Binary file cannot be read as text"
            )
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        if req.offset > 0:
            lines = lines[req.offset :]
        if req.limit > 0:
            lines = lines[: req.limit]

        content = "".join(lines)
        return ToolResult.success(
            data={"path": str(resolved), "content": content, "line_count": len(lines)},
            message=f"Read {len(lines)} lines from {req.path}",
        )

    def _write(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = FileWriteRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        try:
            resolved = contain_path(req.path, self._workspace_root)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.PERMISSION_DENIED, str(exc))

        decision = self._policy.check(ApprovalSubject.PATCH, req.approved)
        if not decision.approved:
            return ToolResult.requires_approval(decision.reason)

        try:
            os.makedirs(resolved.parent, exist_ok=True)
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(req.content)
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        return ToolResult.success(
            data={"path": str(resolved), "bytes_written": len(req.content.encode())},
            message=f"Wrote {len(req.content)} chars to {req.path}",
        )

    def _list(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = FileListRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        try:
            resolved = contain_path(req.path, self._workspace_root)
        except ValueError as exc:
            return ToolResult.failure(ToolErrorCode.PERMISSION_DENIED, str(exc))

        if not resolved.is_dir():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Directory not found: {req.path}"
            )

        try:
            if req.recursive:
                entries: list[str] = []
                for root, dirs, files in os.walk(resolved):
                    depth = Path(root).relative_to(resolved).parts
                    if len(depth) >= req.max_depth:
                        dirs.clear()
                        continue
                    for name in files:
                        entries.append(os.path.join(root, name))
                        if len(entries) >= req.max_entries:
                            break
                    for name in dirs:
                        entries.append(os.path.join(root, name) + os.sep)
                        if len(entries) >= req.max_entries:
                            break
                    if len(entries) >= req.max_entries:
                        break
            else:
                entries = sorted(os.listdir(resolved))
        except OSError as exc:
            return ToolResult.failure(ToolErrorCode.UNKNOWN, str(exc))

        return ToolResult.success(
            data={"path": str(resolved), "entries": entries, "count": len(entries)},
            message=f"Listed {len(entries)} entries in {req.path}",
        )


def __getattr__(name: str) -> type:
    if name == "NoopFileTool":
        import warnings
        warnings.warn(
            "NoopFileTool is deprecated, use RealFileTool instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return RealFileTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
