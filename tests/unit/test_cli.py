"""Tests for CLI argument parsing and entrypoints."""

from __future__ import annotations

from repopilot.cli import build_parser, main


class TestBuildParser:
    """Test CLI argument parser construction."""

    def test_parser_creates_without_error(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_intake_subcommand_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["intake", "https://github.com/o/r/issues/1"])
        assert args.command == "intake"
        assert args.input == "https://github.com/o/r/issues/1"

    def test_intake_with_fixture_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["intake", "bug", "--fixture", "issue.json"])
        assert args.fixture == "issue.json"

    def test_inspect_subcommand_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["inspect", "/some/path"])
        assert args.command == "inspect"
        assert args.path == "/some/path"

    def test_inspect_default_path(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["inspect"])
        assert args.path == "."

    def test_plan_subcommand_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["plan", "bug description", "--repo", "."])
        assert args.command == "plan"

    def test_dry_run_subcommand_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["dry-run", "bug", "--repo", "."])
        assert args.command == "dry-run"

    def test_run_subcommand_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "bug", "--repo", ".", "--max-retries", "3"])
        assert args.command == "run"
        assert args.max_retries == 3

    def test_run_default_test_cmd(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "bug"])
        assert args.test_cmd == "python -m pytest -q"

    def test_no_command_returns_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestMainEntrypoint:
    """Test main() function behavior."""

    def test_no_command_prints_help_and_returns_zero(self) -> None:
        # main() with no args should print help and return 0
        result = main([])
        assert result == 0

    def test_intake_with_valid_input_returns_zero(self) -> None:
        result = main(["intake", "Fix the login bug"])
        assert result == 0

    def test_intake_with_invalid_input_returns_one(self) -> None:
        # Empty input should fail validation
        result = main(["intake", ""])
        assert result == 1

    def test_inspect_nonexistent_path_returns_one(self) -> None:
        result = main(["inspect", "/nonexistent/path/xyz"])
        assert result == 1
