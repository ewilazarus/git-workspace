"""Smoke tests verifying the integration test framework itself."""
from pathlib import Path

from tests.integration.helpers import (
    git_commit,
    git_branch,
    run,
    write_manifest,
    write_hook,
)


def test_cli_is_reachable() -> None:
    result = run("--help")
    assert result.ok
    assert "git-workspace" in result.stdout.lower() or result.returncode == 0


def test_repo_fixture_is_isolated(repo: Path, tmp_path: Path) -> None:
    assert repo == tmp_path
    assert (repo / ".git").exists()


def test_repo_has_initial_commit(repo: Path) -> None:
    import subprocess
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "initial commit" in result.stdout


def test_write_manifest_creates_file(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 7\n')
    assert (repo / ".workspace" / "manifest.toml").exists()


def test_write_hook_is_executable(repo: Path) -> None:
    import os
    hook = write_hook(repo, "after_setup", "#!/bin/sh\necho hello\n")
    assert hook.exists()
    assert os.access(hook, os.X_OK)


def test_git_branch_helper(repo: Path) -> None:
    import subprocess
    git_branch(repo, "feat/test")
    result = subprocess.run(
        ["git", "branch"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert "feat/test" in result.stdout


def test_run_captures_stdout_stderr_returncode(repo: Path) -> None:
    result = run("--help")
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert isinstance(result.returncode, int)


def test_run_result_ok_property(repo: Path) -> None:
    result = run("--help")
    assert result.ok is (result.returncode == 0)
