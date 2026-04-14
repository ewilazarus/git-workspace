import typer
import pytest

from git_workspace.cli.commands.up import up
from git_workspace.cli.commands.prune import prune
from git_workspace.workspace import Workspace


def test_errors_without_threshold_or_manifest(workspace: Workspace) -> None:
    with pytest.raises(typer.BadParameter):
        prune(root=str(workspace.directory))


def test_dry_run_does_not_remove_worktrees(workspace: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace.directory))
    prune(root=str(workspace.directory), older_than_days=-1, dry_run=True)
    assert (workspace.directory / "feat").exists()


def test_apply_removes_worktree(workspace: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace.directory))
    prune(root=str(workspace.directory), older_than_days=-1, dry_run=False)
    assert not (workspace.directory / "feat").exists()


def test_excluded_branch_is_not_pruned(workspace_with_prune: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_prune.directory))
    prune(root=str(workspace_with_prune.directory), older_than_days=-1, dry_run=False)
    assert (workspace_with_prune.directory / "main").exists()


def test_manifest_threshold_used_as_fallback(workspace_with_prune: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace_with_prune.directory))
    # manifest threshold is 30d; fresh worktree has age_days=0, so nothing pruned
    prune(root=str(workspace_with_prune.directory), dry_run=False)
    assert (workspace_with_prune.directory / "feat").exists()


def test_runtime_threshold_overrides_manifest(workspace_with_prune: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace_with_prune.directory))
    prune(root=str(workspace_with_prune.directory), older_than_days=-1, dry_run=False)
    assert not (workspace_with_prune.directory / "feat").exists()


def test_nothing_to_prune_does_not_raise(workspace: Workspace) -> None:
    prune(root=str(workspace.directory), older_than_days=-1, dry_run=False)
