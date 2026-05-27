"""Contracts for planner/executor style agents."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentRole(StrEnum):
    TRIAGE = "triage"
    PLANNER = "planner"
    PATCH = "patch"
    FAILURE_ANALYZER = "failure_analyzer"
    REVIEWER = "reviewer"
    RETRIEVE = "retrieve"


class TriageDecision(BaseModel):
    """Classify the issue before planning."""

    role: AgentRole = AgentRole.TRIAGE
    summary: str
    severity: Severity = Severity.MEDIUM
    likely_area: str | None = None
    requires_human_review: bool = False


class RepairPlannerDecision(BaseModel):
    """Plan a minimal repair before patching."""

    role: AgentRole = AgentRole.PLANNER
    summary: str
    target_files: list[str] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(default_factory=list)


class PatchDecision(BaseModel):
    """Describe a proposed patch without applying it."""

    role: AgentRole = AgentRole.PATCH
    summary: str
    touched_files: list[str] = Field(default_factory=list)
    requires_approval: bool = True


class FailureAnalysisDecision(BaseModel):
    """Analyze a failed test or workflow step."""

    role: AgentRole = AgentRole.FAILURE_ANALYZER
    failure_summary: str
    hypothesis: str
    retry_recommended: bool = False


class ReviewDecision(BaseModel):
    """Review a diff before PR description or publication."""

    role: AgentRole = AgentRole.REVIEWER
    risk_assessment: str
    approved_for_pr: bool = False
    required_followups: list[str] = Field(default_factory=list)
