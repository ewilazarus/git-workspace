"""Integration tests for hook execution timing and environment."""
from pathlib import Path

from tests.integration.helpers import run, write_manifest, write_hook


def _marker(repo: Path, name: str) -> Path:
    return repo / ".workspace" / name


def test_after_setup_runs_on_first_up(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["after_setup"]\n')
    write_hook(repo, "after_setup", f'#!/bin/sh\ntouch {_marker(repo, "after_setup_ran")}\n')

    run("up", "feat/hook", "-r", str(repo))

    assert _marker(repo, "after_setup_ran").exists()


def test_after_activate_runs_on_every_up(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_activate = ["after_activate"]\n')
    counter = _marker(repo, "activate_count")
    write_hook(repo, "after_activate", f'#!/bin/sh\necho x >> {counter}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "-r", str(repo))

    count = len(counter.read_text().strip().splitlines())
    assert count == 3


def test_before_remove_runs_before_worktree_removed(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nbefore_remove = ["before_remove"]\n')
    marker = _marker(repo, "before_remove_ran")
    # Write worktree path to a file so we know it existed when hook ran
    write_hook(
        repo,
        "before_remove",
        f'#!/bin/sh\n[ -d "$GIT_WORKSPACE_WORKTREE" ] && touch {marker}\n',
    )

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo))

    assert marker.exists()


def test_after_remove_runs_after_worktree_removed(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_remove = ["after_remove"]\n')
    marker = _marker(repo, "after_remove_ran")
    write_hook(repo, "after_remove", f'#!/bin/sh\ntouch {marker}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo))

    assert marker.exists()


def test_hooks_receive_gw_worktree_path(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["check_env"]\n')
    recorded = _marker(repo, "worktree_path_env")
    write_hook(repo, "check_env", f'#!/bin/sh\necho "$GIT_WORKSPACE_WORKTREE" > {recorded}\n')

    run("up", "feat/env-test", "-r", str(repo))

    assert recorded.exists()
    assert str(repo / "feat" / "env-test") in recorded.read_text()


def test_hooks_receive_gw_branch(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["check_branch"]\n')
    recorded = _marker(repo, "branch_env")
    write_hook(repo, "check_branch", f'#!/bin/sh\necho "$GIT_WORKSPACE_BRANCH" > {recorded}\n')

    run("up", "feat/env-branch", "-r", str(repo))

    assert "feat/env-branch" in recorded.read_text()


def test_hooks_receive_user_vars(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["check_var"]\n')
    recorded = _marker(repo, "var_env")
    write_hook(repo, "check_var", f'#!/bin/sh\necho "$GIT_WORKSPACE_VAR_MY_VAR" > {recorded}\n')

    run("up", "feat/vars", "-r", str(repo), "--var", "MY_VAR=hello")

    assert "hello" in recorded.read_text()


def test_skip_hooks_suppresses_all_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["after_setup"]\nafter_activate = ["after_activate"]\n')
    write_hook(repo, "after_setup", f'#!/bin/sh\ntouch {_marker(repo, "setup_ran")}\n')
    write_hook(repo, "after_activate", f'#!/bin/sh\ntouch {_marker(repo, "activate_ran")}\n')

    run("up", "feat/nohooks", "-r", str(repo), "--skip-hooks")

    assert not _marker(repo, "setup_ran").exists()
    assert not _marker(repo, "activate_ran").exists()
