"""Retrieval contracts for file, grep, symbol, and embedding search."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from repopilot.repo_analysis import inspect_repository


class RetrievalQuery(BaseModel):
    """Query used by future hybrid retrieval."""

    repository_root: str
    text: str = Field(min_length=1)
    limit: int = 10


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
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
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
        score = float((line_hits * 3) + path_score)
        if score > best_score:
            best_score = score
            best_line_index = index

    if best_score <= 0:
        return None

    start = max(0, best_line_index - 1)
    end = min(len(lines), best_line_index + 2)
    snippet = "\n".join(lines[start:end])
    return best_score, snippet
