"""Approval policy primitives for high-risk operations."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


class ApprovalSubject(StrEnum):
    """Operation categories that may require human approval."""

    PATCH = "patch"
    TEST_EXECUTION = "test_execution"
    GIT = "git"
    GITHUB_WRITE = "github_write"


class ApprovalDecision(BaseModel):
    """Result of checking whether an operation is approved."""

    approved: bool
    subject: ApprovalSubject
    reason: str
    timestamp: str = ""


class ApprovalPolicy(Protocol):
    """Protocol for approval decisions."""

    def check(self, subject: ApprovalSubject, approved: bool = False) -> ApprovalDecision:
        """Return the approval decision for a subject."""


class StrictApprovalPolicy:
    """Default policy: high-risk operations are denied until explicitly approved.

    Maintains an in-memory audit log of all approval decisions.
    """

    def __init__(self) -> None:
        self._log: list[ApprovalDecision] = []

    def check(self, subject: ApprovalSubject, approved: bool = False) -> ApprovalDecision:
        if approved:
            decision = ApprovalDecision(
                approved=True,
                subject=subject,
                reason="Operation was explicitly approved.",
                timestamp=datetime.now(UTC).isoformat(),
            )
        else:
            decision = ApprovalDecision(
                approved=False,
                subject=subject,
                reason=f"{subject.value} requires explicit approval.",
                timestamp=datetime.now(UTC).isoformat(),
            )
        self._log.append(decision)
        return decision

    def audit_log(self) -> list[ApprovalDecision]:
        """Return a copy of the approval audit log."""
        return list(self._log)
