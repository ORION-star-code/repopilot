"""Normalize issue inputs into RepoPilot repair requests."""

from __future__ import annotations

import re

from .issue_fetchers import GitHubIssueReference, IssueFetcher, IssueIntakeError
from .models import RepairRequest

ISSUE_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)"
)


def parse_github_issue_reference(raw_input: str) -> GitHubIssueReference | None:
    """Parse a GitHub issue URL from raw input."""
    match = ISSUE_URL_RE.search(raw_input.strip())
    if not match:
        return None
    repo = f"{match.group('owner')}/{match.group('repo')}"
    return GitHubIssueReference(
        repository=repo,
        issue_number=int(match.group("number")),
        url=match.group(0),
        raw=raw_input,
    )


def normalize_issue_input(
    raw_input: str,
    issue_fetcher: IssueFetcher | None = None,
) -> RepairRequest:
    """Convert a GitHub Issue URL or raw bug text into a structured request."""
    raw = raw_input.strip()
    if not raw:
        raise IssueIntakeError("Issue input cannot be empty.")

    reference = parse_github_issue_reference(raw_input)
    if reference:
        if issue_fetcher:
            return issue_fetcher.fetch(reference)
        return RepairRequest(
            source="github_issue",
            title=f"{reference.repository}#{reference.issue_number}",
            body=raw,
            repository=reference.repository,
            issue_number=reference.issue_number,
            url=reference.url,
            raw=raw_input,
        )

    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), raw)
    title = first_line[:97] + "..." if len(first_line) > 100 else first_line
    return RepairRequest(
        source="bug_description",
        title=title,
        body=raw,
        raw=raw_input,
    )
