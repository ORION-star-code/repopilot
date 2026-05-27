"""Retrieval contracts for file, grep, symbol, and embedding search."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from repopilot.repo_analysis import inspect_repository

MAX_SCORE = 100.0
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB


class RetrievalQuery(BaseModel):
    """Query used by future hybrid retrieval."""

    repository_root: str
    text: str = Field(min_length=1)
    limit: int = 10

    @field_validator("text")
    @classmethod
    def reject_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must contain non-whitespace characters")
        return v


class RetrievedContext(BaseModel):
    """One retrieved code context item."""

    path: str
    score: float
    snippet: str
    source: str


class Retriever(Protocol):
    """Search interface for code context retrieval."""

    def search(self, query: RetrievalQuery) -> list[RetrievedContext]:
        """Return relevant code context."""


class NoopRetriever:
    """Placeholder retriever that performs no repository access."""

    def search(self, query: RetrievalQuery) -> list[RetrievedContext]:
        return []


@lru_cache(maxsize=256)
def _read_file_lines(path: str) -> list[str] | None:
    """Read and cache file lines. Returns None on error."""
    p = Path(path)
    try:
        if p.stat().st_size > MAX_FILE_SIZE_BYTES:
            return None
        return p.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return None


class LocalCodeRetriever:
    """Deterministic read-only retrieval over inspected repository files."""

    def search(self, query: RetrievalQuery) -> list[RetrievedContext]:
        root = Path(query.repository_root).resolve()
        snapshot = inspect_repository(root)
        terms = [term.lower() for term in query.text.split() if term.strip()]
        if not terms:
            return []

        results: list[RetrievedContext] = []
        for relative in snapshot.files:
            path = root / relative
            lines = _read_file_lines(str(path))
            if lines is None:
                continue

            match = _best_match(relative, lines, terms)
            if match is None:
                continue
            score, snippet = match
            results.append(
                RetrievedContext(
                    path=relative,
                    score=score,
                    snippet=snippet,
                    source="local_text",
                )
            )

        return sorted(results, key=lambda item: (-item.score, item.path))[: query.limit]


def _best_match(path: str, lines: list[str], terms: list[str]) -> tuple[float, str] | None:
    best_score = 0.0
    best_line_index = 0
    lower_path = path.lower()
    path_score = sum(1 for term in terms if term in lower_path)

    for index, line in enumerate(lines):
        lower_line = line.lower()
        line_hits = sum(1 for term in terms if term in lower_line)
        score = min(float((line_hits * 3) + path_score), MAX_SCORE)
        if score > best_score:
            best_score = score
            best_line_index = index

    if best_score <= 0:
        return None

    start = max(0, best_line_index - 1)
    end = min(len(lines), best_line_index + 2)
    snippet = "\n".join(lines[start:end])
    return best_score, snippet
