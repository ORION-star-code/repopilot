"""GitHub client contracts with no live side effects in A01."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class GitHubIssue(BaseModel):
    """Structured GitHub issue data used by intake."""

    repository: str
    number: int
    title: str
    body: str
    labels: list[str] = Field(default_factory=list)
    author: str | None = None
    url: str | None = None
    state: Literal["open", "closed"] = "open"
    created_at: str | None = None
    updated_at: str | None = None


class GitHubClient(Protocol):
    """Read-only GitHub client interface."""

    def fetch_issue(self, repository: str, issue_number: int) -> GitHubIssue:
        """Fetch a GitHub issue by repository and number."""


class NoopGitHubClient:
    """Placeholder that makes live GitHub access explicit and unavailable."""

    def fetch_issue(self, repository: str, issue_number: int) -> GitHubIssue:
        return GitHubIssue(
            repository=repository,
            number=issue_number,
            title=f"[noop] Issue #{issue_number}",
            body="Live GitHub access is not implemented. Use fixtures.",
            state="open",
        )
