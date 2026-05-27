"""Offline issue fetcher contracts for intake."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import RepairRequest


@dataclass(frozen=True)
class GitHubIssueReference:
    """Parsed reference to a GitHub issue."""

    repository: str
    issue_number: int
    url: str
    raw: str


class IssueIntakeError(ValueError):
    """Recoverable issue intake error."""


class IssueFixtureError(IssueIntakeError):
    """Recoverable fixture loading or validation error."""


class IssueFetcher(Protocol):
    """Boundary for fetching complete issue data from a parsed reference."""

    def fetch(self, reference: GitHubIssueReference) -> RepairRequest:
        """Return a structured repair request for the issue reference."""


class FixtureIssueFetcher:
    """Load a GitHub issue from a local JSON fixture without network access."""

    def __init__(self, fixture_path: str | Path) -> None:
        self.fixture_path = Path(fixture_path)

    def fetch(self, reference: GitHubIssueReference) -> RepairRequest:
        data = self._load_json()
        repository = self._required_str(data, "repository")
        issue_number = self._required_int(data, "number")

        if repository != reference.repository or issue_number != reference.issue_number:
            raise IssueFixtureError(
                "Fixture issue does not match input URL: "
                f"expected {reference.repository}#{reference.issue_number}, "
                f"got {repository}#{issue_number}."
            )

        return RepairRequest(
            source="github_issue_fixture",
            title=self._required_str(data, "title"),
            body=self._required_str(data, "body"),
            repository=repository,
            issue_number=issue_number,
            url=str(data.get("url") or reference.url),
            labels=self._labels(data),
            author=self._optional_str(data, "author"),
            created_at=self._optional_str(data, "created_at"),
            updated_at=self._optional_str(data, "updated_at"),
            metadata={
                "fixture_path": str(self.fixture_path),
                "fetcher": self.__class__.__name__,
            },
            raw=reference.raw,
        )

    def _load_json(self) -> dict[str, Any]:
        if not self.fixture_path.exists():
            raise IssueFixtureError(f"Issue fixture does not exist: {self.fixture_path}")
        if not self.fixture_path.is_file():
            raise IssueFixtureError(f"Issue fixture is not a file: {self.fixture_path}")

        try:
            payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IssueFixtureError(f"Issue fixture is not valid JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise IssueFixtureError("Issue fixture must be a JSON object.")
        return payload

    @staticmethod
    def _required_str(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise IssueFixtureError(f"Issue fixture field '{key}' must be a non-empty string.")
        return value

    @staticmethod
    def _optional_str(data: dict[str, Any], key: str) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise IssueFixtureError(f"Issue fixture field '{key}' must be a string when present.")
        return value

    @staticmethod
    def _required_int(data: dict[str, Any], key: str) -> int:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise IssueFixtureError(f"Issue fixture field '{key}' must be an integer.")
        return value

    @staticmethod
    def _labels(data: dict[str, Any]) -> list[str]:
        value = data.get("labels", [])
        if not isinstance(value, list):
            raise IssueFixtureError("Issue fixture field 'labels' must be a list.")
        labels: list[str] = []
        for label in value:
            if not isinstance(label, str):
                raise IssueFixtureError("Issue fixture labels must be strings.")
            labels.append(label)
        return labels
