#!/usr/bin/env python3
"""Run the complete RepoPilot validation path."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(label: str, args: list[str]) -> int:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    print(f"\n==> {label}")
    completed = subprocess.run(args, cwd=ROOT, env=env)
    return completed.returncode


def main() -> int:
    checks = [
        ("lint", [sys.executable, "scripts/lint.py"]),
        ("tests", [sys.executable, "-m", "pytest", "-q"]),
        ("harness", [sys.executable, "harness/validate.py"]),
    ]
    for label, args in checks:
        code = run(label, args)
        if code:
            print(f"\nValidation stopped at {label} with exit code {code}.")
            return code
    print("\nRepoPilot validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
