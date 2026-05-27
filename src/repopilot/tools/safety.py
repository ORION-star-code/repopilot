"""Shared safety utilities for path and argument validation."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Git arguments that can execute arbitrary commands or override config
_DANGEROUS_GIT_FLAGS = {
    "--upload-pack",
    "--receive-pack",
    "--exec",
    "--post-receive-hook",
    "--post-update-hook",
    "--pre-receive-hook",
    "--update-hook",
}

# Shell metacharacters that should never appear in git arguments
_SHELL_META_PATTERN = re.compile(r"[;|&$`(){}!\n]")


def contain_path(requested: str, workspace_root: Path) -> Path:
    """Resolve *requested* and ensure it stays within *workspace_root*.

    Raises ``ValueError`` if the resolved path escapes the workspace.
    """
    root = workspace_root.resolve()
    resolved = (root / requested).resolve()
    if not resolved.is_relative_to(root):
        logger.warning(
            "Path traversal attempt blocked: requested=%r resolved=%s root=%s",
            requested, resolved, root,
        )
        raise ValueError(
            f"Path {requested!r} escapes workspace root {root}"
        )
    return resolved


def sanitize_git_args(args: list[str]) -> list[str]:
    """Reject dangerous git arguments.

    Returns the validated list unchanged if safe.  Raises ``ValueError``
    when a dangerous flag or shell metacharacter is detected.
    """
    for arg in args:
        if arg in _DANGEROUS_GIT_FLAGS:
            raise ValueError(f"Dangerous git argument rejected: {arg}")
        # Match --flag=value variants (e.g. --exec=malicious)
        if "=" in arg and arg.split("=", 1)[0] in _DANGEROUS_GIT_FLAGS:
            raise ValueError(f"Dangerous git argument rejected: {arg}")
        if _SHELL_META_PATTERN.search(arg):
            raise ValueError(
                f"Shell metacharacter detected in git argument: {arg!r}"
            )
    return args
