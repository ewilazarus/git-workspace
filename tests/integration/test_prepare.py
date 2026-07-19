import subprocess
from pathlib import Path

import pytest

from git_workspace.cli.commands.prepare import prepare
from git_workspace.cli.commands.up import up
from git_workspace.errors import WorkspacePreparationError, WorktreeNotFoundError
from git_workspace.workspace import Workspace
from git_workspace.workspace.state import WorkspaceStateStore
from tests.helpers import make_context
from tests.integration.conftest import _GIT_ENV


def _store(workspace: Workspace) -> WorkspaceStateStore:
    return WorkspaceStateStore(workspace.paths.state)


def test_prepares_worktree_created_by_up(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="feat", detached=True)
    hook_marker = workspace_with_hooks.dir / ".hook-on-setup"
    hook_marker.unlink()

    prepare(
        ctx=make_context(),
        path=str(workspace_with_hooks.dir / "feat"),
        force=True,
    )

    assert hook_marker.exists()


def test_prepares_raw_git_worktree_at_arbitrary_path(
    workspace_with_hooks: Workspace, tmp_path: Path
) -> None:
    # A worktree created directly with git, outside the workspace root and
    # without git-workspace involvement — the Herdr/external-host scenario.
    outside = tmp_path / "elsewhere" / "raw-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/raw", str(outside)],
        cwd=workspace_with_hooks.dir,
        capture_output=True,
        env=_GIT_ENV,
        check=True,
    )

    prepare(ctx=make_context(), path=str(outside))

    assert (workspace_with_hooks.dir / ".hook-on-setup").exists()
    record = _store(workspace_with_hooks).load(outside)
    assert record is not None
    assert record.lifecycle_state.value == "ready"


def test_prepare_is_a_noop_when_already_ready(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="feat", detached=True)
    hook_marker = workspace_with_hooks.dir / ".hook-on-setup"
    hook_marker.unlink()

    prepare(ctx=make_context(), path=str(workspace_with_hooks.dir / "feat"))

    assert not hook_marker.exists()


def test_prepare_records_ready_state(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main", detached=True)

    record = _store(workspace).load(workspace.dir / "main")

    assert record is not None
    assert record.lifecycle_state.value == "ready"
    assert record.worktree.branch == "main"
    assert record.presentation is None


def test_prepare_rejects_non_worktree_path(workspace: Workspace, tmp_path: Path) -> None:
    not_a_worktree = tmp_path / "plain"
    not_a_worktree.mkdir()

    with pytest.raises(WorktreeNotFoundError):
        prepare(ctx=make_context(str(workspace.dir)), path=str(not_a_worktree))


def test_failed_preparation_records_state_and_is_retryable(
    workspace_with_hooks: Workspace,
) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="feat", detached=True)
    worktree_dir = workspace_with_hooks.dir / "feat"

    # Sabotage the setup hook so preparation fails.
    hook = workspace_with_hooks.paths.bin / "on_setup"
    original = hook.read_bytes()
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)

    with pytest.raises(WorkspacePreparationError):
        prepare(ctx=make_context(), path=str(worktree_dir), force=True)

    record = _store(workspace_with_hooks).load(worktree_dir)
    assert record is not None
    assert record.lifecycle_state.value == "preparation-failed"
    assert record.preparation_error
    assert worktree_dir.is_dir()

    # Repair the hook and retry — prepare must succeed and mark READY.
    hook.write_bytes(original)
    hook.chmod(0o755)

    prepare(ctx=make_context(), path=str(worktree_dir))

    record = _store(workspace_with_hooks).load(worktree_dir)
    assert record is not None
    assert record.lifecycle_state.value == "ready"
