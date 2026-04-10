"""Integration tests for the rm command."""
import subprocess
from pathlib import Path

from tests.integration.helpers import run, write_manifest, write_hook


def test_removes_existing_worktree(repo: Path) -> None:
    run("up", "feat/removeme", "-r", str(repo))
    assert (repo / "feat" / "removeme").is_dir()

    result = run("rm", "feat/removeme", "-r", str(repo))

    assert result.ok, result.stderr
    assert not (repo / "feat" / "removeme").exists()


def test_does_not_delete_branch(repo: Path) -> None:
    run("up", "feat/keepbranch", "-r", str(repo))
    run("rm", "feat/keepbranch", "-r", str(repo))

    result = subprocess.run(
        ["git", "branch"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert "feat/keepbranch" in result.stdout


def test_cleans_up_empty_parent_directories(repo: Path) -> None:
    run("up", "feat/cleanup", "-r", str(repo))
    run("rm", "feat/cleanup", "-r", str(repo))

    assert not (repo / "feat").exists()


def test_fails_on_dirty_worktree_without_force(repo: Path) -> None:
    run("up", "feat/dirty", "-r", str(repo))
    (repo / "feat" / "dirty" / "uncommitted.txt").write_text("dirty\n")

    result = run("rm", "feat/dirty", "-r", str(repo))

    assert not result.ok
    assert (repo / "feat" / "dirty").exists()


def test_force_removes_dirty_worktree(repo: Path) -> None:
    run("up", "feat/dirty", "-r", str(repo))
    (repo / "feat" / "dirty" / "uncommitted.txt").write_text("dirty\n")

    result = run("rm", "feat/dirty", "-r", str(repo), "--force")

    assert result.ok, result.stderr
    assert not (repo / "feat" / "dirty").exists()


def test_fails_for_nonexistent_worktree(repo: Path) -> None:
    result = run("rm", "feat/ghost", "-r", str(repo))

    assert not result.ok
    assert "feat/ghost" in result.stderr


def test_executes_remove_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nbefore_remove = ["mark_remove"]\n')
    marker = repo / ".workspace" / "removed"
    write_hook(repo, "mark_remove", f'#!/bin/sh\ntouch {marker}\n')

    run("up", "feat/hook-test", "-r", str(repo))
    result = run("rm", "feat/hook-test", "-r", str(repo))

    assert result.ok, result.stderr
    assert marker.exists()


def test_skip_hooks_prevents_remove_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nbefore_remove = ["mark_remove"]\n')
    marker = repo / ".workspace" / "removed"
    write_hook(repo, "mark_remove", f'#!/bin/sh\ntouch {marker}\n')

    run("up", "feat/hook-test", "-r", str(repo))
    run("rm", "feat/hook-test", "-r", str(repo), "--skip-hooks")

    assert not marker.exists()


def test_supports_branch_inference_from_cwd(repo: Path) -> None:
    run("up", "feat/infer", "-r", str(repo))
    worktree = repo / "feat" / "infer"

    result = run("rm", cwd=worktree)

    assert result.ok, result.stderr
    assert not worktree.exists()
