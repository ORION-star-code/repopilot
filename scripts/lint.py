#!/usr/bin/env python3
"""Run static checks for the RepoPilot architecture skeleton."""

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
    try:
        completed = subprocess.run(args, cwd=ROOT, env=env)
    except FileNotFoundError:
        print(f"Missing command for {label}: {args[0]}")
        return 127
    return completed.returncode


def main() -> int:
    checks = [
        ("ruff", [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts", "harness"]),
        ("mypy", [sys.executable, "-m", "mypy", "src"]),
    ]
    for label, args in checks:
        code = run(label, args)
        if code:
            print(f"\nStatic checks stopped at {label} with exit code {code}.")
            return code
    print("\nStatic checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
