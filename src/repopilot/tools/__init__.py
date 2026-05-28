"""Tool contracts exposed to agents and workflows."""

from __future__ import annotations

from .contracts import Tool, ToolCategory, ToolErrorCode, ToolResult
from .file import RealFileTool
from .git import RealGitTool
from .patch import PatchExecutionResult, PatchProposal, RealPatchTool
from .safety import contain_path, sanitize_git_args
from .search import RealSearchTool
from .test_runner import NoopTestRunnerTool, TestExecutionRequest, TestExecutionResult

__all__ = [
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
    "contain_path",
    "sanitize_git_args",
]


def __getattr__(name: str) -> object:
    """Lazy deprecation aliases for Noop tools."""
    _deprecated = {
        "NoopFileTool": (".file", "RealFileTool"),
        "NoopGitTool": (".git", "RealGitTool"),
        "NoopPatchTool": (".patch", "RealPatchTool"),
        "NoopSearchTool": (".search", "RealSearchTool"),
    }
    if name in _deprecated:
        import importlib
        import warnings

        module_path, real_name = _deprecated[name]
        warnings.warn(
            f"{name} is deprecated, use {real_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        module = importlib.import_module(module_path, __package__)
        return getattr(module, real_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
