"""Repository inspection helpers for RepoPilot."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import RepoFile, RepoSnapshot

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
}

CODE_SUFFIXES = {
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}

CONFIG_FILENAMES = {
    ".env.example",
    ".github/workflows/ci.yml",
    ".github/workflows/test.yml",
    "Dockerfile",
    "Makefile",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "tox.ini",
}

ENTRYPOINT_FILENAMES = {
    "__main__.py",
    "app.py",
    "cli.py",
    "main.py",
    "manage.py",
    "server.py",
}

DOCUMENTATION_SUFFIXES = {".md"}


def inspect_repository(root: str | Path) -> RepoSnapshot:
    """Build a lightweight searchable inventory for a repository path."""
    resolved = Path(root).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Repository path does not exist: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {resolved}")

    files: list[str] = []
    file_details: list[RepoFile] = []
    language_counts: Counter[str] = Counter()
    for path in sorted(resolved.rglob("*")):
        if not path.is_file() or _is_excluded(path, resolved):
            continue
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        relative = path.relative_to(resolved).as_posix()
        category = _classify_file(relative, path)
        files.append(relative)
        file_details.append(
            RepoFile(
                path=relative,
                suffix=path.suffix.lower() or "<none>",
                size_bytes=path.stat().st_size,
                line_count=_line_count(path),
                category=category,
            )
        )
        language_counts[path.suffix.lower() or "<none>"] += 1

    test_files = [detail.path for detail in file_details if detail.category == "test"]
    config_files = [detail.path for detail in file_details if detail.category == "config"]
    entrypoint_files = [detail.path for detail in file_details if detail.category == "entrypoint"]
    important_files = _important_files(file_details)

    return RepoSnapshot(
        root=str(resolved),
        files=files,
        language_counts=dict(sorted(language_counts.items())),
        file_details=file_details,
        test_files=test_files,
        config_files=config_files,
        entrypoint_files=entrypoint_files,
        important_files=important_files,
    )


def _is_excluded(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in EXCLUDED_DIRS for part in relative_parts)


def _classify_file(relative: str, path: Path) -> str:
    lower_relative = relative.lower()
    name = path.name
    lower_name = name.lower()

    if relative in CONFIG_FILENAMES or name in CONFIG_FILENAMES:
        return "config"
    if lower_relative.startswith(".github/workflows/"):
        return "config"
    if _is_test_file(lower_relative, lower_name):
        return "test"
    if name in ENTRYPOINT_FILENAMES:
        return "entrypoint"
    if path.suffix.lower() in DOCUMENTATION_SUFFIXES:
        return "documentation"
    return "source"


def _is_test_file(lower_relative: str, lower_name: str) -> bool:
    return (
        lower_relative.startswith("tests/")
        or "/tests/" in lower_relative
        or lower_name.startswith("test_")
        or lower_name.endswith("_test.py")
        or lower_name.endswith(".test.ts")
        or lower_name.endswith(".spec.ts")
        or lower_name.endswith(".test.tsx")
        or lower_name.endswith(".spec.tsx")
        or lower_name.endswith(".test.js")
        or lower_name.endswith(".spec.js")
        or lower_name.endswith(".test.jsx")
        or lower_name.endswith(".spec.jsx")
    )


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except UnicodeDecodeError:
        return 0


def _important_files(file_details: list[RepoFile]) -> list[str]:
    priority = {"config": 0, "entrypoint": 1, "test": 2, "source": 3, "documentation": 4}
    ordered = sorted(
        file_details,
        key=lambda detail: (
            priority.get(detail.category, 99),
            detail.path.count("/"),
            detail.path,
        ),
    )
    return [detail.path for detail in ordered[:20]]
