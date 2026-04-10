"""
Integration test fixtures and helpers.

This module provides:
- `run`: CLI invocation helper (subprocess-based)
- `git_init`, `git_commit`, `git_branch`, `git_config`: Git helper utilities
- `repo`: Isolated temporary Git repository fixture
- `write_manifest`: Workspace manifest helper
- `write_hook`: Hook script fixture helper
"""
from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# CLI invocation helper
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Result of a CLI invocation."""

    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(*args: str, cwd: Path | None = None) -> RunResult:
    """
    Invoke the installed git-workspace CLI with the given arguments.

    :param args: Arguments to pass to git-workspace
    :param cwd: Working directory for the subprocess
    :returns: RunResult with stdout, stderr, and returncode
    """
    result = subprocess.run(
        ["git-workspace", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    return RunResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


# ---------------------------------------------------------------------------
# Git helper utilities
# ---------------------------------------------------------------------------


def git_config(repo: Path, name: str = "Test User", email: str = "test@example.com") -> None:
    """Set Git user config in a repository."""
    subprocess.run(["git", "config", "user.name", name], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", email], cwd=str(repo), check=True)


def git_init(path: Path, default_branch: str = "main") -> None:
    """Initialize a Git repository with a default branch name."""
    subprocess.run(
        ["git", "init", "-b", default_branch, str(path)],
        check=True,
        capture_output=True,
    )
    git_config(path)


def git_commit(repo: Path, message: str = "initial commit", allow_empty: bool = False) -> str:
    """
    Create a commit in the repository.

    :param repo: Repository path
    :param message: Commit message
    :param allow_empty: Whether to allow empty commits
    :returns: The short commit SHA
    """
    cmd = ["git", "commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")
    subprocess.run(cmd, cwd=str(repo), check=True, capture_output=True)
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_add(repo: Path, *paths: str) -> None:
    """Stage files in the repository."""
    subprocess.run(["git", "add", *paths], cwd=str(repo), check=True, capture_output=True)


def git_branch(repo: Path, branch: str, checkout: bool = False) -> None:
    """Create a branch, optionally checking it out."""
    subprocess.run(["git", "branch", branch], cwd=str(repo), check=True, capture_output=True)
    if checkout:
        subprocess.run(["git", "checkout", branch], cwd=str(repo), check=True, capture_output=True)


# ---------------------------------------------------------------------------
# Repository fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """
    Provide an isolated temporary Git repository with an initial commit.

    Each test gets its own fresh repository under tmp_path. The repository
    has Git user config set and one initial commit on main.
    """
    git_init(tmp_path)
    (tmp_path / "README").write_text("workspace\n")
    git_add(tmp_path, "README")
    git_commit(tmp_path, "initial commit")
    return tmp_path


# ---------------------------------------------------------------------------
# Workspace manifest helper
# ---------------------------------------------------------------------------


def write_manifest(repo: Path, content: str) -> Path:
    """
    Write a manifest.toml into .workspace/ in the given repository.

    :param repo: Repository path
    :param content: TOML content for the manifest
    :returns: Path to the written manifest file
    """
    workspace_dir = repo / ".workspace"
    workspace_dir.mkdir(exist_ok=True)
    manifest_path = workspace_dir / "manifest.toml"
    manifest_path.write_text(content)
    return manifest_path


# ---------------------------------------------------------------------------
# Hook script fixture helper
# ---------------------------------------------------------------------------


def write_hook(repo: Path, name: str, script: str) -> Path:
    """
    Write an executable hook script into .workspace/bin/.

    :param repo: Repository path
    :param name: Script filename (e.g. "after_setup")
    :param script: Shell script content (should start with a shebang)
    :returns: Path to the written script
    """
    bin_dir = repo / ".workspace" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_path = bin_dir / name
    script_path.write_text(script)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path
