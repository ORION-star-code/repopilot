"""Contracts for repair output artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from repopilot.runs import RunRecord


class ArtifactBundle(BaseModel):
    """Structured outputs produced by a repair run."""

    run_id: str
    diff: str
    test_report: str
    risk_assessment: str
    pr_description: str
    artifact_refs: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ArtifactsWriter:
    """Build and persist artifact bundles."""

    def build_bundle(
        self,
        run: RunRecord,
        diff: str,
        test_report: str,
        risk_assessment: str,
        pr_description: str,
    ) -> ArtifactBundle:
        """Return a structured artifact bundle for downstream persistence."""
        return ArtifactBundle(
            run_id=run.run_id,
            diff=diff,
            test_report=test_report,
            risk_assessment=risk_assessment,
            pr_description=pr_description,
            artifact_refs=list(run.artifact_refs),
        )

    def save_to_disk(self, bundle: ArtifactBundle, output_dir: str) -> list[str]:
        """Persist artifact bundle to disk. Returns list of written file paths."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        files = {
            "diff.patch": bundle.diff,
            "test_report.txt": bundle.test_report,
            "risk_assessment.txt": bundle.risk_assessment,
            "pr_description.md": bundle.pr_description,
        }

        written: list[str] = []
        for name, content in files.items():
            if not content:
                continue
            path = out / name
            path.write_text(content, encoding="utf-8")
            written.append(str(path))

        # Write summary
        summary_path = out / "summary.txt"
        summary_lines = [
            f"Run ID: {bundle.run_id}",
            f"Generated: {bundle.generated_at.isoformat()}",
            f"Artifacts: {len(written)} files",
        ]
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        written.append(str(summary_path))

        return written
