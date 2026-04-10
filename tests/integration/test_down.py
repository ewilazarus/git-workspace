"""Integration tests for the down command."""
from pathlib import Path

from tests.integration.helpers import run, write_manifest, write_hook


def test_outputs_worktree_path(repo: Path) -> None:
    run("up", "feat/branch", "-r", str(repo))

    result = run("down", "feat/branch", "-r", str(repo))

    assert result.ok, result.stderr
    assert str(repo / "feat" / "branch") in result.stdout


def test_runs_on_deactivate_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["mark_deactivate"]\n')
    marker = repo / ".workspace" / "deactivated"
    write_hook(repo, "mark_deactivate", f'#!/bin/sh\ntouch {marker}\n')

    run("up", "feat/branch", "-r", str(repo))
    result = run("down", "feat/branch", "-r", str(repo))

    assert result.ok, result.stderr
    assert marker.exists()


def test_does_not_remove_worktree(repo: Path) -> None:
    run("up", "feat/branch", "-r", str(repo))

    run("down", "feat/branch", "-r", str(repo))

    assert (repo / "feat" / "branch").is_dir()


def test_skip_hooks_suppresses_on_deactivate(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["mark_deactivate"]\n')
    marker = repo / ".workspace" / "deactivated"
    write_hook(repo, "mark_deactivate", f'#!/bin/sh\ntouch {marker}\n')

    run("up", "feat/branch", "-r", str(repo))
    result = run("down", "feat/branch", "-r", str(repo), "--skip-hooks")

    assert result.ok, result.stderr
    assert not marker.exists()


def test_infers_branch_from_cwd(repo: Path) -> None:
    run("up", "feat/branch", "-r", str(repo))
    worktree = repo / "feat" / "branch"

    result = run("down", cwd=worktree)

    assert result.ok, result.stderr


def test_fails_for_nonexistent_worktree(repo: Path) -> None:
    result = run("down", "feat/ghost", "-r", str(repo))

    assert not result.ok
    assert "feat/ghost" in result.stderr


def test_json_output(repo: Path) -> None:
    import json
    run("up", "feat/branch", "-r", str(repo))

    result = run("down", "feat/branch", "-r", str(repo), "--json")

    assert result.ok, result.stderr
    data = json.loads(result.stdout)
    assert data["branch"] == "feat/branch"
    assert str(repo / "feat" / "branch") in data["path"]


def test_forwards_vars_to_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["check_var"]\n')
    recorded = repo / ".workspace" / "var_value"
    write_hook(repo, "check_var", f'#!/bin/sh\necho "$GIT_WORKSPACE_VAR_MY_VAR" > {recorded}\n')

    run("up", "feat/branch", "-r", str(repo))
    run("down", "feat/branch", "-r", str(repo), "--var", "MY_VAR=goodbye")

    assert "goodbye" in recorded.read_text()
