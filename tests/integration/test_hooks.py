"""Integration tests for hook execution timing and environment."""
from pathlib import Path

from tests.integration.helpers import run, write_manifest, write_hook


def _marker(repo: Path, name: str) -> Path:
    return repo / ".workspace" / name


# ---------------------------------------------------------------------------
# on_setup
# ---------------------------------------------------------------------------

def test_on_setup_runs_on_first_up(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_setup = ["on_setup"]\n')
    write_hook(repo, "on_setup", f'#!/bin/sh\ntouch {_marker(repo, "on_setup_ran")}\n')

    run("up", "feat/hook", "-r", str(repo))

    assert _marker(repo, "on_setup_ran").exists()


def test_on_setup_does_not_run_on_resume(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_setup = ["on_setup"]\n')
    counter = _marker(repo, "setup_count")
    write_hook(repo, "on_setup", f'#!/bin/sh\necho x >> {counter}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "-r", str(repo))

    count = len(counter.read_text().strip().splitlines()) if counter.exists() else 0
    assert count == 1


# ---------------------------------------------------------------------------
# on_activate
# ---------------------------------------------------------------------------

def test_on_activate_runs_on_every_up(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_activate = ["on_activate"]\n')
    counter = _marker(repo, "activate_count")
    write_hook(repo, "on_activate", f'#!/bin/sh\necho x >> {counter}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "-r", str(repo))

    count = len(counter.read_text().strip().splitlines())
    assert count == 3


# ---------------------------------------------------------------------------
# on_attach
# ---------------------------------------------------------------------------

def test_on_attach_runs_when_not_detached(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_attach = ["on_attach"]\n')
    write_hook(repo, "on_attach", f'#!/bin/sh\ntouch {_marker(repo, "on_attach_ran")}\n')

    run("up", "feat/hook", "-r", str(repo))

    assert _marker(repo, "on_attach_ran").exists()



def test_on_attach_does_not_run_in_detached_mode(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_attach = ["on_attach"]\n')
    write_hook(repo, "on_attach", f'#!/bin/sh\ntouch {_marker(repo, "on_attach_ran")}\n')

    run("up", "feat/hook", "--detached", "-r", str(repo))

    assert not _marker(repo, "on_attach_ran").exists()


def test_on_activate_runs_in_both_attached_and_detached_mode(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_activate = ["on_activate"]\n')
    counter = _marker(repo, "activate_count")
    write_hook(repo, "on_activate", f'#!/bin/sh\necho x >> {counter}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("up", "feat/hook", "--detached", "-r", str(repo))

    count = len(counter.read_text().strip().splitlines())
    assert count == 2


# ---------------------------------------------------------------------------
# on_deactivate
# ---------------------------------------------------------------------------

def test_on_deactivate_runs_on_rm(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["on_deactivate"]\n')
    write_hook(repo, "on_deactivate", f'#!/bin/sh\ntouch {_marker(repo, "on_deactivate_ran")}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo))

    assert _marker(repo, "on_deactivate_ran").exists()


def test_on_deactivate_runs_before_worktree_removed(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["on_deactivate"]\n')
    marker = _marker(repo, "on_deactivate_ran")
    write_hook(
        repo,
        "on_deactivate",
        f'#!/bin/sh\n[ -d "$GIT_WORKSPACE_WORKTREE" ] && touch {marker}\n',
    )

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo))

    assert marker.exists()


def test_on_deactivate_skip_hooks_suppresses_it(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_deactivate = ["on_deactivate"]\n')
    write_hook(repo, "on_deactivate", f'#!/bin/sh\ntouch {_marker(repo, "on_deactivate_ran")}\n')

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo), "--skip-hooks")

    assert not _marker(repo, "on_deactivate_ran").exists()


# ---------------------------------------------------------------------------
# on_remove
# ---------------------------------------------------------------------------

def test_on_remove_runs_before_worktree_removed(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_remove = ["on_remove"]\n')
    marker = _marker(repo, "on_remove_ran")
    write_hook(
        repo,
        "on_remove",
        f'#!/bin/sh\n[ -d "$GIT_WORKSPACE_WORKTREE" ] && touch {marker}\n',
    )

    run("up", "feat/hook", "-r", str(repo))
    run("rm", "feat/hook", "-r", str(repo))

    assert marker.exists()


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

def test_hooks_receive_gw_worktree_path(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_setup = ["check_env"]\n')
    recorded = _marker(repo, "worktree_path_env")
    write_hook(repo, "check_env", f'#!/bin/sh\necho "$GIT_WORKSPACE_WORKTREE" > {recorded}\n')

    run("up", "feat/env-test", "-r", str(repo))

    assert recorded.exists()
    assert str(repo / "feat" / "env-test") in recorded.read_text()


def test_hooks_receive_gw_branch(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_setup = ["check_branch"]\n')
    recorded = _marker(repo, "branch_env")
    write_hook(repo, "check_branch", f'#!/bin/sh\necho "$GIT_WORKSPACE_BRANCH" > {recorded}\n')

    run("up", "feat/env-branch", "-r", str(repo))

    assert "feat/env-branch" in recorded.read_text()


def test_hooks_receive_user_vars(repo: Path) -> None:
    write_manifest(repo, '[hooks]\non_setup = ["check_var"]\n')
    recorded = _marker(repo, "var_env")
    write_hook(repo, "check_var", f'#!/bin/sh\necho "$GIT_WORKSPACE_VAR_MY_VAR" > {recorded}\n')

    run("up", "feat/vars", "-r", str(repo), "--var", "MY_VAR=hello")

    assert "hello" in recorded.read_text()


# ---------------------------------------------------------------------------
# --skip-hooks
# ---------------------------------------------------------------------------

def test_skip_hooks_suppresses_all_hooks(repo: Path) -> None:
    write_manifest(
        repo,
        '[hooks]\non_setup = ["on_setup"]\non_activate = ["on_activate"]\non_attach = ["on_attach"]\n',
    )
    write_hook(repo, "on_setup", f'#!/bin/sh\ntouch {_marker(repo, "setup_ran")}\n')
    write_hook(repo, "on_activate", f'#!/bin/sh\ntouch {_marker(repo, "activate_ran")}\n')
    write_hook(repo, "on_attach", f'#!/bin/sh\ntouch {_marker(repo, "attach_ran")}\n')

    run("up", "feat/nohooks", "-r", str(repo), "--skip-hooks")

    assert not _marker(repo, "setup_ran").exists()
    assert not _marker(repo, "activate_ran").exists()
    assert not _marker(repo, "attach_ran").exists()
