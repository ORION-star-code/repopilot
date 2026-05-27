"""Approval policy primitives for high-risk operations."""

from __future__ import annotations

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


class ApprovalPolicy(Protocol):
    """Protocol for approval decisions."""

    def check(self, subject: ApprovalSubject, approved: bool = False) -> ApprovalDecision:
        """Return the approval decision for a subject."""


class StrictApprovalPolicy:
    """Default policy: high-risk operations are denied until explicitly approved."""

    def check(self, subject: ApprovalSubject, approved: bool = False) -> ApprovalDecision:
        if approved:
            return ApprovalDecision(
                approved=True,
                subject=subject,
                reason="Operation was explicitly approved.",
            )
        return ApprovalDecision(
            approved=False,
            subject=subject,
            reason=f"{subject.value} requires explicit approval.",
        )
