"""GitHub integration boundary."""

from __future__ import annotations

from .client import GitHubClient, GitHubIssue, NoopGitHubClient

__all__ = ["GitHubClient", "GitHubIssue", "NoopGitHubClient"]
