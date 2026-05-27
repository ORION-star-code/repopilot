"""Tool contracts exposed to agents and workflows."""

from __future__ import annotations

from .contracts import Tool, ToolCategory, ToolErrorCode, ToolResult
from .file import NoopFileTool, RealFileTool
from .git import NoopGitTool, RealGitTool
from .patch import NoopPatchTool, PatchExecutionResult, PatchProposal, RealPatchTool
from .search import NoopSearchTool, RealSearchTool
from .test_runner import NoopTestRunnerTool, TestExecutionRequest, TestExecutionResult

__all__ = [
    "NoopFileTool",
    "NoopGitTool",
    "NoopPatchTool",
    "NoopSearchTool",
    "NoopTestRunnerTool",
    "PatchExecutionResult",
    "PatchProposal",
    "RealFileTool",
    "RealGitTool",
    "RealPatchTool",
    "RealSearchTool",
    "TestExecutionRequest",
    "TestExecutionResult",
    "Tool",
    "ToolCategory",
    "ToolErrorCode",
    "ToolResult",
]
