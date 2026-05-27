"""Security boundary tests for path containment, arg sanitization, and sandbox."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from repopilot.sandbox import CommandRequest, SubprocessSandboxExecutor
from repopilot.tools.safety import contain_path, sanitize_git_args

# --- contain_path ---


class TestContainPath:
    """Test path traversal prevention in contain_path."""

    def test_relative_path_within_workspace(self, tmp_path: Path) -> None:
        result = contain_path("src/app.py", tmp_path)
        assert result.is_relative_to(tmp_path.resolve())

    def test_absolute_path_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes workspace root"):
            contain_path("/etc/passwd", tmp_path)

    def test_dot_dot_traversal_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        with pytest.raises(ValueError, match="escapes workspace root"):
            contain_path("sub/../../etc/passwd", tmp_path)

    def test_dot_dot_at_root_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes workspace root"):
            contain_path("../escape", tmp_path)

    @pytest.mark.skipif(sys.platform == "win32", reason="symlinks require admin on Windows")
    def test_symlink_to_outside_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside_target"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "link"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="escapes workspace root"):
            contain_path("link", tmp_path)

    def test_path_resolves_to_workspace_root(self, tmp_path: Path) -> None:
        result = contain_path(".", tmp_path)
        assert result == tmp_path.resolve()

    def test_nested_valid_path(self, tmp_path: Path) -> None:
        (tmp_path / "a" / "b").mkdir(parents=True)
        result = contain_path("a/b/c.py", tmp_path)
        assert result == (tmp_path / "a" / "b" / "c.py").resolve()


# --- sanitize_git_args ---


class TestSanitizeGitArgs:
    """Test git argument injection prevention."""

    def test_clean_args_pass(self) -> None:
        result = sanitize_git_args(["--no-pager", "log", "-5"])
        assert result == ["--no-pager", "log", "-5"]

    def test_empty_args_pass(self) -> None:
        result = sanitize_git_args([])
        assert result == []

    def test_dangerous_exec_flag_rejected(self) -> None:
        with pytest.raises(ValueError, match="Dangerous git argument"):
            sanitize_git_args(["--exec=malicious"])

    def test_dangerous_upload_pack_rejected(self) -> None:
        with pytest.raises(ValueError, match="Dangerous git argument"):
            sanitize_git_args(["--upload-pack"])

    def test_shell_semicolon_rejected(self) -> None:
        with pytest.raises(ValueError, match="Shell metacharacter"):
            sanitize_git_args(["--message=foo; rm -rf /"])

    def test_shell_pipe_rejected(self) -> None:
        with pytest.raises(ValueError, match="Shell metacharacter"):
            sanitize_git_args(["arg|cat /etc/passwd"])

    def test_shell_backtick_rejected(self) -> None:
        with pytest.raises(ValueError, match="Shell metacharacter"):
            sanitize_git_args(["`whoami`"])

    def test_shell_dollar_rejected(self) -> None:
        with pytest.raises(ValueError, match="Shell metacharacter"):
            sanitize_git_args(["$(whoami)"])


# --- SubprocessSandboxExecutor cwd validation ---


class TestSandboxCwdValidation:
    """Test that sandbox executor validates cwd against workspace root."""

    def test_relative_cwd_within_workspace(self, tmp_path: Path) -> None:
        executor = SubprocessSandboxExecutor(workspace_root=tmp_path)
        (tmp_path / "sub").mkdir()
        request = CommandRequest(
            command=["python", "-c", "print('ok')"],
            cwd="sub",
        )
        result = executor.run(request)
        assert result.exit_code == 0

    def test_absolute_cwd_outside_workspace_rejected(self, tmp_path: Path) -> None:
        executor = SubprocessSandboxExecutor(workspace_root=tmp_path)
        request = CommandRequest(
            command=["python", "-c", "print('ok')"],
            cwd="/etc",
        )
        result = executor.run(request)
        assert result.exit_code == 126
        assert "escapes workspace root" in result.stderr

    def test_none_cwd_allowed(self, tmp_path: Path) -> None:
        executor = SubprocessSandboxExecutor(workspace_root=tmp_path)
        request = CommandRequest(command=["python", "-c", "print('ok')"])
        result = executor.run(request)
        assert result.exit_code == 0

    def test_dot_dot_cwd_rejected(self, tmp_path: Path) -> None:
        executor = SubprocessSandboxExecutor(workspace_root=tmp_path)
        request = CommandRequest(
            command=["python", "-c", "print('ok')"],
            cwd="../../escape",
        )
        result = executor.run(request)
        assert result.exit_code == 126
