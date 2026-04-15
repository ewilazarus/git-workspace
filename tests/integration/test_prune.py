import pytest
import typer

from git_workspace.cli.commands.prune import prune
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_errors_without_threshold_or_manifest(workspace: Workspace) -> None:
    with pytest.raises(typer.BadParameter):
        prune(root=str(workspace.dir))


def test_dry_run_does_not_remove_worktrees(workspace: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace.dir))
    prune(root=str(workspace.dir), older_than_days=-1, dry_run=True)
    assert (workspace.dir / "feat").exists()


def test_apply_removes_worktree(workspace: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace.dir))
    prune(root=str(workspace.dir), older_than_days=-1, dry_run=False)
    assert not (workspace.dir / "feat").exists()


def test_excluded_branch_is_not_pruned(workspace_with_prune: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_prune.dir))
    prune(root=str(workspace_with_prune.dir), older_than_days=-1, dry_run=False)
    assert (workspace_with_prune.dir / "main").exists()


def test_manifest_threshold_used_as_fallback(workspace_with_prune: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace_with_prune.dir))
    # manifest threshold is 30d; fresh worktree has age_days=0, so nothing pruned
    prune(root=str(workspace_with_prune.dir), dry_run=False)
    assert (workspace_with_prune.dir / "feat").exists()


def test_runtime_threshold_overrides_manifest(workspace_with_prune: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace_with_prune.dir))
    prune(root=str(workspace_with_prune.dir), older_than_days=-1, dry_run=False)
    assert not (workspace_with_prune.dir / "feat").exists()


def test_nothing_to_prune_does_not_raise(workspace: Workspace) -> None:
    prune(root=str(workspace.dir), older_than_days=-1, dry_run=False)
