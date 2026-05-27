"""Search tool with real keyword and grep-based code search."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from repopilot.retrieval.contracts import LocalCodeRetriever, RetrievalQuery

from .contracts import ToolCategory, ToolErrorCode, ToolResult

logger = logging.getLogger(__name__)

MAX_PATTERN_LENGTH = 500
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB

_IGNORED_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# Patterns that indicate catastrophic backtracking risk
_NESTED_QUANTIFIER_PATTERN = re.compile(r"\([^)]*[+*][^)]*\)[+*]")


class KeywordSearchRequest(BaseModel):
    """Request for keyword-based code search."""

    repository_root: str
    query: str = Field(min_length=1)
    limit: int = 10


class GrepSearchRequest(BaseModel):
    """Request for grep-like pattern search."""

    repository_root: str
    pattern: str = Field(min_length=1)
    glob: str = "*.py"
    max_results: int = 20


class RealSearchTool:
    """Search tool that performs real code search."""

    name = "search"
    category = ToolCategory.SEARCH
    approval_required = False

    def __init__(self) -> None:
        self._retriever = LocalCodeRetriever()

    def run(self, arguments: Mapping[str, Any]) -> ToolResult:
        action = arguments.get("action", "keyword")
        if action == "keyword":
            return self._keyword_search(arguments)
        if action == "grep":
            return self._grep_search(arguments)
        return ToolResult.failure(
            ToolErrorCode.INVALID_INPUT,
            f"Unknown action: {action}. Use 'keyword' or 'grep'.",
        )

    def _keyword_search(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = KeywordSearchRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        if not os.path.isdir(req.repository_root):
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Directory not found: {req.repository_root}"
            )

        query = RetrievalQuery(
            repository_root=req.repository_root,
            text=req.query,
            limit=req.limit,
        )
        results = self._retriever.search(query)
        return ToolResult.success(
            data={
                "results": [r.model_dump() for r in results],
                "count": len(results),
            },
            message=f"Found {len(results)} results for '{req.query}'",
        )

    def _grep_search(self, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            req = GrepSearchRequest.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.failure(ToolErrorCode.INVALID_INPUT, str(exc))

        root = Path(req.repository_root)
        if not root.is_dir():
            return ToolResult.failure(
                ToolErrorCode.NOT_FOUND, f"Directory not found: {req.repository_root}"
            )

        # ReDoS protection: pattern length check
        if len(req.pattern) > MAX_PATTERN_LENGTH:
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT,
                f"Pattern too long ({len(req.pattern)} chars, limit {MAX_PATTERN_LENGTH})",
            )

        # ReDoS protection: nested quantifier detection
        if _NESTED_QUANTIFIER_PATTERN.search(req.pattern):
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT,
                "Pattern contains nested quantifiers which risk catastrophic backtracking",
            )

        try:
            regex = re.compile(req.pattern)
        except re.error as exc:
            return ToolResult.failure(
                ToolErrorCode.INVALID_INPUT, f"Invalid regex: {exc}"
            )

        matches: list[dict[str, Any]] = []
        for filepath in root.rglob(req.glob):
            if not filepath.is_file():
                continue
            # Skip ignored directories
            if any(part in _IGNORED_DIR_NAMES for part in filepath.parts):
                continue
            # File size guard
            try:
                if filepath.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue
            try:
                lines = filepath.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({
                        "path": str(filepath.relative_to(root)),
                        "line": line_num,
                        "content": line.rstrip(),
                    })
                    if len(matches) >= req.max_results:
                        break
            if len(matches) >= req.max_results:
                break

        return ToolResult.success(
            data={"matches": matches, "count": len(matches)},
            message=f"Found {len(matches)} matches for pattern '{req.pattern}'",
        )


# Backward-compatible alias
NoopSearchTool = RealSearchTool
