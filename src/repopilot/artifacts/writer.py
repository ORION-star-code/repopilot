"""Contracts for repair output artifacts."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from repopilot.runs import RunRecord
from repopilot.tools.safety import contain_path


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

    def save_to_disk(
        self,
        bundle: ArtifactBundle,
        output_dir: str,
        workspace_root: Path | None = None,
    ) -> list[str]:
        """Persist artifact bundle to disk. Returns list of written file paths."""
        root = workspace_root or Path.cwd()
        # If output_dir is absolute and within root, use it directly;
        # otherwise validate through contain_path
        output_path = Path(output_dir)
        if output_path.is_absolute():
            resolved_dir = output_path.resolve()
            if not resolved_dir.is_relative_to(root.resolve()):
                raise ValueError(
                    f"Output directory {output_dir!r} escapes workspace {root}"
                )
        else:
            try:
                resolved_dir = contain_path(output_dir, root)
            except ValueError as exc:
                raise ValueError(f"Output directory escapes workspace: {exc}") from exc

        resolved_dir.mkdir(parents=True, exist_ok=True)

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
            path = resolved_dir / name
            self._atomic_write(path, content)
            written.append(str(path))

        # Write summary
        summary_path = resolved_dir / "summary.txt"
        summary_lines = [
            f"Run ID: {bundle.run_id}",
            f"Generated: {bundle.generated_at.isoformat()}",
            f"Artifacts: {len(written)} files",
        ]
        self._atomic_write(summary_path, "\n".join(summary_lines) + "\n")
        written.append(str(summary_path))

        return written

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content atomically via temp file + os.replace."""
        try:
            encoded = content.encode("utf-8")
        except UnicodeEncodeError:
            encoded = content.encode("utf-8", errors="replace")

        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, suffix=".tmp", prefix=path.stem
        )
        try:
            os.write(fd, encoded)
            os.close(fd)
            os.replace(tmp_path, path)
        except BaseException:
            os.close(fd) if not _fd_closed(fd) else None
            Path(tmp_path).unlink(missing_ok=True)
            raise


def _fd_closed(fd: int) -> bool:
    """Check if a file descriptor is already closed."""
    try:
        os.fstat(fd)
        return False
    except OSError:
        return True
